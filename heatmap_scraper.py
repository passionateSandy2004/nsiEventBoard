"""
NSE Heatmap Interactive Scraper
================================

Interactive scraper for NSE heatmap that:
1. Shows main categories
2. Shows index cards for selected category
3. Scrapes heatmap data for selected index

Usage:
    python heatmap_scraper.py
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


class HeatmapScraper:
    """Interactive scraper for NSE Heatmap"""
    
    def __init__(self, headless=False):
        """Initialize the scraper"""
        self.url = "https://www.nseindia.com/market-data/live-market-indices/heatmap"
        self.headless = headless
        self.driver = None
        
        # Category mappings
        self.categories = {
            '1': 'Broad Market Indices',
            '2': 'Sectoral Indices',
            '3': 'Thematic Indices',
            '4': 'Strategy Indices'
        }
    
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
        """Navigate to heatmap page"""
        try:
            logger.info(f"Navigating to: {self.url}")
            self.driver.get(self.url)
            time.sleep(5)  # Wait for page load
            
            # Wait for content to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            logger.info("Page loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading page: {e}")
            return False
    
    def select_category(self, category_key):
        """
        Select a category by clicking on it
        
        Args:
            category_key: '1' for Broad Market, '2' for Sectoral, etc.
        """
        try:
            category_name = self.categories[category_key]
            logger.info(f"Selecting category: {category_name}")
            
            # Find and click the category
            # Categories are usually in a sidebar or tab structure
            category_element = self.driver.find_element(
                By.XPATH, 
                f"//div[contains(text(), '{category_name}')] | //a[contains(text(), '{category_name}')]"
            )
            category_element.click()
            time.sleep(2)  # Wait for content to load
            
            logger.info(f"Category '{category_name}' selected")
            return True
            
        except Exception as e:
            logger.error(f"Error selecting category: {e}")
            # Category might already be selected, continue
            return True
    
    def get_index_cards(self):
        """
        Scrape all index cards from current view
        
        Returns:
            list: List of index card data
        """
        try:
            logger.info("Scraping index cards...")
            
            # Wait for cards to load
            time.sleep(3)
            
            # Try multiple selectors to find the index cards
            index_cards = []
            
            # Method 1: Look for clickable divs/links with NIFTY in them
            try:
                # These are usually anchor tags or divs that are clickable
                cards = self.driver.find_elements(By.CSS_SELECTOR, "a, div[onclick], div[class*='clickable']")
                
                logger.info(f"Found {len(cards)} potential clickable elements")
                
                for card in cards:
                    try:
                        card_text = card.text.strip()
                        
                        # Check if it contains NIFTY and has numbers (value/percentage)
                        if 'NIFTY' in card_text.upper() and any(char.isdigit() for char in card_text):
                            lines = [line.strip() for line in card_text.split('\n') if line.strip()]
                            
                            if lines:
                                index_name = lines[0]
                                value = ""
                                change = ""
                                
                                # Try to extract value and change from remaining lines
                                for line in lines[1:]:
                                    if any(char.isdigit() for char in line):
                                        if not value:
                                            parts = line.split()
                                            value = parts[0] if parts else line
                                            change = parts[1] if len(parts) > 1 else ""
                                        elif not change and '%' in line:
                                            change = line
                                
                                index_cards.append({
                                    'number': len(index_cards) + 1,
                                    'name': index_name,
                                    'value': value,
                                    'change': change,
                                    'element': card
                                })
                    except:
                        continue
            
            except Exception as e:
                logger.warning(f"Method 1 failed: {e}")
            
            # Method 2: If Method 1 didn't find cards, try getting all visible text elements
            if len(index_cards) == 0:
                try:
                    # Get all elements with visible text
                    all_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'NIFTY')]")
                    
                    logger.info(f"Method 2: Found {len(all_elements)} elements with NIFTY")
                    
                    for element in all_elements:
                        try:
                            # Try to find the parent clickable element
                            parent = element.find_element(By.XPATH, "./ancestor::*[@onclick or self::a][1]")
                            
                            text = parent.text.strip()
                            
                            if text and any(char.isdigit() for char in text):
                                lines = [line.strip() for line in text.split('\n') if line.strip()]
                                
                                if lines:
                                    index_cards.append({
                                        'number': len(index_cards) + 1,
                                        'name': lines[0],
                                        'value': lines[1] if len(lines) > 1 else '',
                                        'change': lines[2] if len(lines) > 2 else '',
                                        'element': parent
                                    })
                        except:
                            # Element might not have clickable parent
                            try:
                                text = element.text.strip()
                                if text and len(text) > 5:
                                    index_cards.append({
                                        'number': len(index_cards) + 1,
                                        'name': text,
                                        'value': '',
                                        'change': '',
                                        'element': element
                                    })
                            except:
                                continue
                
                except Exception as e:
                    logger.warning(f"Method 2 failed: {e}")
            
            # Remove duplicates based on name
            seen_names = set()
            unique_cards = []
            for card in index_cards:
                if card['name'] not in seen_names:
                    seen_names.add(card['name'])
                    unique_cards.append(card)
            
            logger.info(f"Found {len(unique_cards)} unique index cards")
            return unique_cards
            
        except Exception as e:
            logger.error(f"Error scraping index cards: {e}")
            return []
    
    def click_index_card(self, card_element):
        """
        Click on an index card to open heatmap
        
        Args:
            card_element: Selenium WebElement of the card
        """
        try:
            logger.info("Clicking index card...")
            
            # Try to get the href and extract the JavaScript function
            try:
                href = card_element.get_attribute('href')
                if href and 'javascript:' in href:
                    # Extract and execute the JavaScript function
                    js_function = href.replace('javascript:', '')
                    logger.info(f"Executing JavaScript: {js_function[:100]}...")
                    self.driver.execute_script(js_function)
                    time.sleep(3)  # Wait for heatmap to load
                    logger.info("JavaScript executed successfully")
                    return True
            except:
                pass
            
            # Method 2: JavaScript click (bypasses intercept issues)
            try:
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", card_element)
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", card_element)
                time.sleep(3)
                logger.info("JavaScript click successful")
                return True
            except Exception as e:
                logger.warning(f"JavaScript click failed: {e}")
            
            # Method 3: Regular click with better positioning
            try:
                # Scroll to top first to avoid navigation bar
                self.driver.execute_script("window.scrollTo(0, 400);")
                time.sleep(0.5)
                
                # Scroll element into view
                self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", card_element)
                time.sleep(1)
                
                # Try regular click
                card_element.click()
                time.sleep(3)
                logger.info("Regular click successful")
                return True
            except Exception as e:
                logger.error(f"All click methods failed: {e}")
                return False
            
        except Exception as e:
            logger.error(f"Error clicking card: {e}")
            return False
    
    def scrape_heatmap(self):
        """
        Scrape heatmap data after clicking an index
        
        Returns:
            dict: Heatmap data with all stocks
        """
        try:
            logger.info("Scraping heatmap data...")
            
            # Wait for heatmap to load
            time.sleep(4)
            
            heatmap_data = {
                'scrape_timestamp': datetime.now().isoformat(),
                'stocks': []
            }
            
            # Method 1: Look for heatmap-specific tiles
            try:
                # These are the actual stock tiles in the heatmap
                stock_tiles = self.driver.find_elements(
                    By.CSS_SELECTOR, 
                    "div[class*='heatmap'], div[id*='heatmap'], a[class*='tile'], div[class*='tile']"
                )
                
                logger.info(f"Found {len(stock_tiles)} potential heatmap tiles")
                
                for tile in stock_tiles:
                    try:
                        text = tile.text.strip()
                        
                        # Skip empty or very short text
                        if not text or len(text) < 3:
                            continue
                        
                        # Skip navigation elements
                        if any(skip in text.lower() for skip in ['scan qr', 'download', 'login', 'nse go', 'ncfm', 'back']):
                            continue
                        
                        lines = [line.strip() for line in text.split('\n') if line.strip()]
                        
                        # Valid stock tile should have: Symbol, Price, Change%
                        if len(lines) >= 2:
                            symbol = lines[0]
                            
                            # Check if it looks like a stock symbol (short, uppercase)
                            if len(symbol) < 20 and symbol.isupper():
                                stock_data = {
                                    'symbol': symbol,
                                    'price': lines[1] if len(lines) > 1 else '',
                                    'change': lines[2] if len(lines) > 2 else '',
                                    'raw_text': text
                                }
                                
                                # Get background color (indicates gain/loss)
                                try:
                                    bg_color = tile.value_of_css_property('background-color')
                                    stock_data['color'] = bg_color
                                    
                                    # Determine if gain or loss based on color
                                    if 'rgb' in bg_color:
                                        # Parse RGB values
                                        rgb = bg_color.replace('rgba', '').replace('rgb', '').replace('(', '').replace(')', '')
                                        r, g, b = [int(x.split(',')[i].strip()) if i < len(x.split(',')) else 0 for i, x in enumerate([rgb])]
                                        
                                        # Green if g > r, Red if r > g
                                        if g > r:
                                            stock_data['trend'] = 'gain'
                                        elif r > g:
                                            stock_data['trend'] = 'loss'
                                        else:
                                            stock_data['trend'] = 'neutral'
                                except:
                                    stock_data['color'] = 'unknown'
                                    stock_data['trend'] = 'unknown'
                                
                                heatmap_data['stocks'].append(stock_data)
                    
                    except:
                        continue
                
            except Exception as e:
                logger.warning(f"Method 1 failed: {e}")
            
            # Method 2: Look specifically for elements with stock-like text patterns
            if len(heatmap_data['stocks']) == 0:
                try:
                    # Get all text elements
                    all_elements = self.driver.find_elements(By.XPATH, "//*[text()]")
                    
                    logger.info(f"Method 2: Analyzing {len(all_elements)} text elements")
                    
                    processed_texts = set()
                    
                    for element in all_elements:
                        try:
                            text = element.text.strip()
                            
                            if not text or text in processed_texts:
                                continue
                            
                            processed_texts.add(text)
                            
                            # Skip common non-stock text
                            if any(skip in text.lower() for skip in [
                                'scan qr', 'download', 'login', 'nse go', 'ncfm', 
                                'back', 'streaming', 'as on', 'nifty 50', 'nifty next'
                            ]):
                                continue
                            
                            lines = [line.strip() for line in text.split('\n') if line.strip()]
                            
                            # Pattern: SYMBOL \n PRICE CHANGE%
                            if len(lines) == 2 or len(lines) == 3:
                                symbol = lines[0]
                                
                                # Check if first line looks like a symbol
                                if len(symbol) <= 20 and symbol.isupper() and not symbol.startswith('NIFTY'):
                                    # Second line should have numbers
                                    if len(lines) > 1 and any(char.isdigit() for char in lines[1]):
                                        parts = lines[1].split()
                                        
                                        stock_data = {
                                            'symbol': symbol,
                                            'price': parts[0] if parts else lines[1],
                                            'change': parts[1] if len(parts) > 1 else (lines[2] if len(lines) > 2 else ''),
                                            'raw_text': text
                                        }
                                        
                                        # Try to get parent element color
                                        try:
                                            parent = element.find_element(By.XPATH, "./ancestor::*[1]")
                                            bg_color = parent.value_of_css_property('background-color')
                                            stock_data['color'] = bg_color
                                        except:
                                            stock_data['color'] = 'unknown'
                                        
                                        heatmap_data['stocks'].append(stock_data)
                        
                        except:
                            continue
                
                except Exception as e:
                    logger.warning(f"Method 2 failed: {e}")
            
            # Remove duplicates based on symbol
            seen_symbols = set()
            unique_stocks = []
            for stock in heatmap_data['stocks']:
                if stock['symbol'] not in seen_symbols:
                    seen_symbols.add(stock['symbol'])
                    unique_stocks.append(stock)
            
            heatmap_data['stocks'] = unique_stocks
            
            logger.info(f"Scraped {len(heatmap_data['stocks'])} stocks from heatmap")
            return heatmap_data
            
        except Exception as e:
            logger.error(f"Error scraping heatmap: {e}")
            return None
    
    def take_screenshot(self, filename):
        """Take screenshot of current page"""
        try:
            filepath = f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            self.driver.save_screenshot(filepath)
            logger.info(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
            return None
    
    def save_data(self, data, filename):
        """Save data to JSON file"""
        try:
            filepath = f"{filename}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Data saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            return None
    
    def cleanup(self):
        """Close browser"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed")
            except:
                pass


def main():
    """Main interactive function"""
    print("\n" + "=" * 80)
    print("NSE HEATMAP INTERACTIVE SCRAPER")
    print("=" * 80)
    
    # Ask for headless mode
    headless_input = input("\nRun in headless mode? (y/n, default: n): ").strip().lower()
    headless = headless_input == 'y'
    
    # Initialize scraper
    scraper = HeatmapScraper(headless=headless)
    
    try:
        # Initialize driver
        if not scraper._init_driver():
            print("❌ Failed to initialize browser")
            return
        
        # Navigate to page
        if not scraper.navigate_to_page():
            print("❌ Failed to load page")
            return
        
        # Step 1: Select Category
        print("\n" + "=" * 80)
        print("STEP 1: SELECT MAIN CATEGORY")
        print("=" * 80)
        print("\nAvailable Categories:")
        for key, name in scraper.categories.items():
            print(f"  {key}. {name}")
        
        category_choice = input("\nEnter category number (1-4): ").strip()
        
        if category_choice not in scraper.categories:
            print("❌ Invalid category")
            return
        
        scraper.select_category(category_choice)
        
        # Step 2: Show Index Cards
        print("\n" + "=" * 80)
        print("STEP 2: AVAILABLE INDICES")
        print("=" * 80)
        
        index_cards = scraper.get_index_cards()
        
        if not index_cards:
            print("❌ No index cards found")
            print("Taking screenshot for debugging...")
            scraper.take_screenshot("heatmap_debug")
            return
        
        print(f"\nFound {len(index_cards)} indices:")
        for card in index_cards:
            print(f"  {card['number']}. {card['name']} - {card['value']} ({card['change']})")
        
        # Step 3: Select Index and Scrape Heatmap
        print("\n" + "=" * 80)
        print("STEP 3: SELECT INDEX TO VIEW HEATMAP")
        print("=" * 80)
        
        index_choice = input(f"\nEnter index number (1-{len(index_cards)}): ").strip()
        
        try:
            index_num = int(index_choice)
            if 1 <= index_num <= len(index_cards):
                selected_card = index_cards[index_num - 1]
                
                print(f"\n✅ Selected: {selected_card['name']}")
                print("Clicking index to open heatmap...")
                
                # Click the card
                if scraper.click_index_card(selected_card['element']):
                    # Take screenshot of heatmap
                    print("\nTaking screenshot of heatmap...")
                    scraper.take_screenshot(f"heatmap_{selected_card['name'].replace(' ', '_')}")
                    
                    # Scrape heatmap data
                    print("\nScraping heatmap data...")
                    heatmap_data = scraper.scrape_heatmap()
                    
                    if heatmap_data:
                        # Add metadata
                        heatmap_data['index_name'] = selected_card['name']
                        heatmap_data['index_value'] = selected_card['value']
                        heatmap_data['index_change'] = selected_card['change']
                        heatmap_data['category'] = scraper.categories[category_choice]
                        
                        # Save data
                        filepath = scraper.save_data(
                            heatmap_data, 
                            f"heatmap_{selected_card['name'].replace(' ', '_')}"
                        )
                        
                        print(f"\n✅ Heatmap data scraped successfully!")
                        print(f"   Total stocks: {len(heatmap_data.get('stocks', []))}")
                        print(f"   Data saved to: {filepath}")
                    else:
                        print("⚠️  Could not scrape heatmap data")
                else:
                    print("❌ Failed to click index card")
            else:
                print("❌ Invalid index number")
        
        except ValueError:
            print("❌ Invalid input")
        
        # Wait before closing
        input("\nPress Enter to close browser...")
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        scraper.cleanup()
    
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()

