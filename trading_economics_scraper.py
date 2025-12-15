"""
Trading Economics Calendar Scraper
===================================

Scrapes economic calendar data from Trading Economics.
Extracts events, dates, countries, importance levels, and actual/forecast values.

Usage:
    python trading_economics_scraper.py
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import json
import time
from datetime import datetime
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradingEconomicsScraper:
    """Scraper for Trading Economics Calendar"""
    
    def __init__(self, headless=False):
        """Initialize the scraper"""
        self.url = "https://tradingeconomics.com/calendar"
        self.headless = headless
        self.driver = None
        
    def _init_driver(self):
        """Initialize web driver"""
        try:
            options = webdriver.ChromeOptions()
            if self.headless:
                options.add_argument('--headless')
                options.add_argument('--disable-gpu')
            
            # Anti-bot detection
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--window-size=1920,1080')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.wait = WebDriverWait(self.driver, 20)
            
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("WebDriver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing WebDriver: {e}")
            return False
    
    def navigate_to_page(self):
        """Navigate to Trading Economics calendar page"""
        try:
            logger.info(f"Navigating to {self.url}")
            self.driver.get(self.url)
            
            # Wait for page to load and JavaScript to execute
            logger.info("Waiting for page to load...")
            time.sleep(8)
            
            # Wait for any calendar content to appear
            try:
                # Try multiple selectors that Trading Economics might use
                selectors = [
                    (By.TAG_NAME, "table"),
                    (By.CSS_SELECTOR, "[class*='calendar']"),
                    (By.CSS_SELECTOR, "[id*='calendar']"),
                    (By.CSS_SELECTOR, "[class*='event']"),
                    (By.CSS_SELECTOR, "tbody tr"),
                    (By.CSS_SELECTOR, "[data-event]")
                ]
                
                found = False
                for by, selector in selectors:
                    try:
                        self.wait.until(EC.presence_of_element_located((by, selector)))
                        logger.info(f"Found element: {selector}")
                        found = True
                        break
                    except TimeoutException:
                        continue
                
                if not found:
                    logger.warning("No calendar elements found, but page loaded")
                
                # Additional wait for dynamic content
                time.sleep(3)
                
                logger.info("Page loaded successfully")
                return True
                
            except Exception as e:
                logger.warning(f"Wait timeout, but continuing: {e}")
                return True
                
        except Exception as e:
            logger.error(f"Error navigating to page: {e}")
            return False
    
    def scrape_calendar(self):
        """Scrape calendar events from the page"""
        try:
            logger.info("Starting to scrape calendar events...")
            
            # Scroll to load more content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(2)
            
            events = []
            
            # Method 1: Try to find table rows (most common structure)
            try:
                # Look for table rows - Trading Economics uses table structure
                rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr, table tr")
                
                logger.info(f"Found {len(rows)} table rows")
                
                # Filter out header rows
                for i, row in enumerate(rows):
                    try:
                        if not row.is_displayed():
                            continue
                        
                        # Skip header rows
                        row_classes = row.get_attribute('class') or ''
                        if 'header' in row_classes.lower() or 'thead' in row_classes.lower():
                            continue
                        
                        cells = row.find_elements(By.TAG_NAME, "td")
                        
                        if len(cells) < 2:  # Need at least some data
                            continue
                        
                        # Extract data from cells
                        # Typical structure: Date | Time | Country | Event | Actual | Forecast | Previous
                        cell_texts = []
                        for cell in cells:
                            text = cell.text.strip()
                            if text:
                                cell_texts.append(text)
                        
                        if len(cell_texts) >= 2:
                            event_data = {
                                'row_index': i,
                                'date': cell_texts[0] if len(cell_texts) > 0 else '',
                                'time': cell_texts[1] if len(cell_texts) > 1 else '',
                                'country': cell_texts[2] if len(cell_texts) > 2 else '',
                                'event': cell_texts[3] if len(cell_texts) > 3 else '',
                                'actual': cell_texts[4] if len(cell_texts) > 4 else '',
                                'forecast': cell_texts[5] if len(cell_texts) > 5 else '',
                                'previous': cell_texts[6] if len(cell_texts) > 6 else '',
                                'raw_cells': cell_texts
                            }
                            
                            # Try to get importance level (usually in a class or data attribute)
                            try:
                                importance_attrs = row.find_elements(By.CSS_SELECTOR, "[class*='importance'], [class*='impact'], [data-importance], [class*='high'], [class*='medium'], [class*='low']")
                                if importance_attrs:
                                    importance = importance_attrs[0].get_attribute('class') or importance_attrs[0].get_attribute('data-importance') or ''
                                    event_data['importance'] = importance
                                else:
                                    # Check row itself
                                    row_class = row.get_attribute('class') or ''
                                    if any(level in row_class.lower() for level in ['high', 'medium', 'low', 'importance']):
                                        event_data['importance'] = row_class
                                    else:
                                        event_data['importance'] = ''
                            except:
                                event_data['importance'] = ''
                            
                            # Get country flag or icon if available
                            try:
                                flag_img = row.find_element(By.CSS_SELECTOR, "img[src*='flag'], img[alt*='flag'], [class*='flag']")
                                event_data['country_flag'] = flag_img.get_attribute('src') or flag_img.get_attribute('alt') or ''
                            except:
                                event_data['country_flag'] = ''
                            
                            events.append(event_data)
                            
                    except Exception as e:
                        logger.debug(f"Error processing row {i}: {e}")
                        continue
                
                logger.info(f"Scraped {len(events)} events from table")
                
            except Exception as e:
                logger.warning(f"Table method failed: {e}")
            
            # Method 2: Try to find calendar event elements (div-based structure)
            if len(events) == 0:
                logger.info("Trying alternative method: looking for calendar event divs...")
                try:
                    # Look for common calendar event selectors
                    event_elements = self.driver.find_elements(
                        By.CSS_SELECTOR,
                        "[class*='calendar'], [class*='event'], [class*='row'], [data-event]"
                    )
                    
                    logger.info(f"Found {len(event_elements)} potential event elements")
                    
                    for elem in event_elements:
                        try:
                            if not elem.is_displayed():
                                continue
                            
                            text = elem.text.strip()
                            if not text or len(text) < 10:
                                continue
                            
                            # Try to extract structured data
                            event_data = {
                                'text': text,
                                'html': elem.get_attribute('outerHTML')[:200] if elem.get_attribute('outerHTML') else ''
                            }
                            
                            events.append(event_data)
                            
                        except:
                            continue
                    
                    logger.info(f"Scraped {len(events)} events from divs")
                    
                except Exception as e:
                    logger.warning(f"Div method failed: {e}")
            
            # Method 3: Get all text content and parse
            if len(events) == 0:
                logger.info("Trying fallback method: extracting all page text...")
                try:
                    body = self.driver.find_element(By.TAG_NAME, "body")
                    page_text = body.text
                    
                    # Split by lines and look for event-like patterns
                    lines = [line.strip() for line in page_text.split('\n') if line.strip()]
                    
                    event_data = {
                        'method': 'text_extraction',
                        'total_lines': len(lines),
                        'sample_lines': lines[:50]  # First 50 lines as sample
                    }
                    
                    events.append(event_data)
                    
                except Exception as e:
                    logger.error(f"Text extraction failed: {e}")
            
            return events
            
        except Exception as e:
            logger.error(f"Error scraping calendar: {e}")
            return []
    
    def get_page_info(self):
        """Get additional page information"""
        try:
            info = {
                'url': self.driver.current_url,
                'title': self.driver.title,
                'page_source_length': len(self.driver.page_source),
                'timestamp': datetime.now().isoformat()
            }
            
            # Try to find date filters or other UI elements
            try:
                date_elements = self.driver.find_elements(By.CSS_SELECTOR, "[class*='date'], [id*='date'], input[type='date']")
                info['date_filters_found'] = len(date_elements)
            except:
                info['date_filters_found'] = 0
            
            # Count various elements
            try:
                info['tables_found'] = len(self.driver.find_elements(By.TAG_NAME, "table"))
                info['rows_found'] = len(self.driver.find_elements(By.CSS_SELECTOR, "tr"))
                info['calendar_elements'] = len(self.driver.find_elements(By.CSS_SELECTOR, "[class*='calendar'], [id*='calendar']"))
            except:
                pass
            
            return info
            
        except Exception as e:
            logger.error(f"Error getting page info: {e}")
            return {}
    
    def save_screenshot(self, filename=None):
        """Save a screenshot for debugging"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"trading_economics_screenshot_{timestamp}.png"
            
            self.driver.save_screenshot(filename)
            logger.info(f"Screenshot saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving screenshot: {e}")
            return None
    
    def save_page_source(self, filename=None):
        """Save page HTML source for debugging"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"trading_economics_source_{timestamp}.html"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            
            logger.info(f"Page source saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Error saving page source: {e}")
            return None
    
    def save_data(self, events, filename=None):
        """Save scraped data to JSON file"""
        try:
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"trading_economics_calendar_{timestamp}.json"
            
            data = {
                'scrape_timestamp': datetime.now().isoformat(),
                'url': self.url,
                'total_events': len(events),
                'events': events,
                'page_info': self.get_page_info()
            }
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Data saved to {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            return None
    
    def cleanup(self):
        """Close driver"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Driver closed")
            except:
                pass
    
    def run(self, save_file=None, debug=False):
        """Run the complete scraping process"""
        try:
            if not self._init_driver():
                return None
            
            if not self.navigate_to_page():
                return None
            
            # Save debug files if requested
            if debug:
                self.save_screenshot()
                self.save_page_source()
            
            events = self.scrape_calendar()
            
            if save_file:
                filename = self.save_data(events, save_file)
                return filename
            else:
                return events
                
        except Exception as e:
            logger.error(f"Error in run: {e}")
            return None
        finally:
            self.cleanup()


def main():
    """Main function"""
    import sys
    
    print("\n" + "=" * 80)
    print("TRADING ECONOMICS CALENDAR SCRAPER")
    print("=" * 80)
    print("\nStarting scraper...")
    print("This will scrape economic calendar events from Trading Economics.\n")
    
    # Check for debug flag
    debug = '--debug' in sys.argv or '-d' in sys.argv
    
    scraper = TradingEconomicsScraper(headless=False)
    
    try:
        result = scraper.run(debug=debug)
        
        if result:
            print(f"\n✓ Scraping completed!")
            if isinstance(result, list):
                print(f"  Found {len(result)} events/data points")
                
                if len(result) > 0:
                    print(f"\nSample event:")
                    print(json.dumps(result[0], indent=2))
                    
                    # Save to file
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"trading_economics_calendar_{timestamp}.json"
                    scraper.save_data(result, filename)
                    print(f"\n✓ Data saved to {filename}")
            else:
                print(f"  Data saved to: {result}")
        else:
            print("\n✗ Scraping failed")
            if debug:
                print("Debug files (screenshot and HTML) have been saved for inspection.")
            
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.cleanup()


if __name__ == '__main__':
    main()


