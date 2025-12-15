"""
NSE Announcements Monitor
=========================

Automated scraper that monitors the NSE Corporate Announcements page every 5 minutes
and saves the data in JSON format.

Features:
- Runs every 5 minutes
- Outputs JSON format
- Real-time monitoring
- Multiple market types (Equity, SME, Debt, MF, etc.)
- Incremental updates
- Error recovery

Usage:
    python announcements_monitor.py
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
import os
import schedule

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('announcements_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AnnouncementsMonitor:
    """Monitor NSE Corporate Announcements page and scrape data every 5 minutes"""
    
    def __init__(self, headless=True, output_dir='announcements_data', market_type='Equity'):
        """
        Initialize the monitor
        
        Args:
            headless (bool): Run browser in headless mode
            output_dir (str): Directory to save JSON files
            market_type (str): Market type to monitor ('Equity', 'SME', 'Debt', 'MF', etc.)
        """
        self.output_dir = output_dir
        self.url = "https://www.nseindia.com/companies-listing/corporate-filings-announcements"
        self.market_type = market_type
        self.driver = None
        self.headless = headless
        self.last_data = None
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info("AnnouncementsMonitor initialized")
        logger.info(f"Market Type: {self.market_type}")
        logger.info(f"Output directory: {self.output_dir}")
    
    def _init_driver(self):
        """Initialize or reinitialize the web driver"""
        try:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            
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
            
            # Hide webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("WebDriver initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing WebDriver: {e}")
            return False
    
    def _wait_for_table(self):
        """Wait for table to be present on page"""
        try:
            table = self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            time.sleep(2)  # Additional wait for data to populate
            return True
        except TimeoutException:
            logger.error("Timeout waiting for table to load")
            return False
    
    def _select_market_type(self):
        """Select the appropriate market type tab"""
        if self.market_type == 'Equity':
            return True  # Equity is default
        
        try:
            # Try to click the market type tab
            tab = self.driver.find_element(By.XPATH, f"//a[text()='{self.market_type}']")
            tab.click()
            time.sleep(3)  # Wait for content to load
            logger.info(f"Switched to {self.market_type} tab")
            return True
        except NoSuchElementException:
            logger.warning(f"Could not find {self.market_type} tab, using current tab")
            return False
    
    def _extract_table_headers(self):
        """Extract table headers"""
        try:
            headers = self.driver.find_elements(By.CSS_SELECTOR, "table thead th")
            return [h.text.strip() for h in headers if h.text.strip()]
        except Exception as e:
            logger.error(f"Error extracting headers: {e}")
            return []
    
    def _extract_table_data(self):
        """Extract all data from current page"""
        try:
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            data = []
            
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if cells:
                    row_data = []
                    for cell in cells:
                        # Get text content
                        text = cell.text.strip()
                        
                        # Try to get link if exists (for symbols, attachments, etc.)
                        try:
                            link = cell.find_element(By.TAG_NAME, "a")
                            href = link.get_attribute('href')
                            if href:
                                # Check if it's a PDF or XBRL
                                if '.pdf' in href.lower():
                                    text = {
                                        'text': text,
                                        'link': href,
                                        'type': 'pdf'
                                    }
                                elif 'xbrl' in href.lower():
                                    text = {
                                        'text': text,
                                        'link': href,
                                        'type': 'xbrl'
                                    }
                                else:
                                    text = {
                                        'text': text,
                                        'link': href,
                                        'type': 'link'
                                    }
                        except NoSuchElementException:
                            pass
                        
                        row_data.append(text)
                    
                    if row_data:
                        data.append(row_data)
            
            return data
        except Exception as e:
            logger.error(f"Error extracting table data: {e}")
            return []
    
    def _has_next_page(self):
        """Check if there's a next page available"""
        try:
            next_button = self.driver.find_element(
                By.XPATH, 
                "//button[contains(text(), 'Next')]"
            )
            return next_button.is_enabled() and 'disabled' not in next_button.get_attribute('class')
        except NoSuchElementException:
            return False
    
    def _click_next_page(self):
        """Click next page button"""
        try:
            next_button = self.driver.find_element(
                By.XPATH, 
                "//button[contains(text(), 'Next')]"
            )
            
            if next_button.is_enabled() and 'disabled' not in next_button.get_attribute('class'):
                next_button.click()
                time.sleep(3)  # Wait for page to load
                return True
            return False
        except Exception as e:
            logger.error(f"Error clicking next page: {e}")
            return False
    
    def scrape_all_pages(self, max_pages=None):
        """
        Scrape all pages of announcements
        
        Args:
            max_pages (int): Maximum number of pages to scrape (None for all)
        
        Returns:
            dict: Scraped data with metadata
        """
        try:
            # Initialize driver if needed
            if not self.driver:
                if not self._init_driver():
                    return None
            
            # Navigate to page
            logger.info(f"Navigating to: {self.url}")
            self.driver.get(self.url)
            time.sleep(5)  # Initial page load
            
            # Select market type
            self._select_market_type()
            
            # Wait for table
            if not self._wait_for_table():
                logger.error("Table not found on page")
                return None
            
            # Get headers
            headers = self._extract_table_headers()
            if not headers:
                logger.warning("No headers found, using generic column names")
                headers = ['SYMBOL', 'COMPANY NAME', 'SUBJECT', 'DETAILS', 'ATTACHMENT', 'XBRL', 'BROADCAST DATE/TIME']
            
            logger.info(f"Table headers: {headers}")
            
            # Scrape all pages
            all_data = []
            page = 1
            
            while True:
                if max_pages and page > max_pages:
                    logger.info(f"Reached maximum page limit: {max_pages}")
                    break
                
                logger.info(f"Scraping page {page}...")
                
                page_data = self._extract_table_data()
                all_data.extend(page_data)
                logger.info(f"Extracted {len(page_data)} rows from page {page}")
                
                # Check if there's a next page
                if not self._has_next_page():
                    logger.info("No more pages available")
                    break
                
                # Go to next page
                if not self._click_next_page():
                    logger.info("Could not navigate to next page")
                    break
                
                page += 1
                
                # Safety limit
                if page > 100:
                    logger.warning("Reached page limit of 100")
                    break
            
            logger.info(f"Total rows scraped: {len(all_data)}")
            
            # Convert to structured format
            structured_data = []
            for row in all_data:
                if len(row) >= len(headers):
                    row_dict = {}
                    for i, header in enumerate(headers):
                        row_dict[header] = row[i] if i < len(row) else ''
                    structured_data.append(row_dict)
                else:
                    # Handle mismatched columns
                    row_dict = {}
                    for i, value in enumerate(row):
                        header = headers[i] if i < len(headers) else f"Column_{i+1}"
                        row_dict[header] = value
                    structured_data.append(row_dict)
            
            # Create result object
            result = {
                'metadata': {
                    'scrape_timestamp': datetime.now().isoformat(),
                    'total_records': len(structured_data),
                    'total_pages': page,
                    'market_type': self.market_type,
                    'source_url': self.url,
                    'headers': headers
                },
                'data': structured_data
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error during scraping: {e}")
            return None
    
    def save_json(self, data, filename_prefix='announcements'):
        """
        Save data to JSON file
        
        Args:
            data (dict): Data to save
            filename_prefix (str): Prefix for filename
        """
        if not data:
            logger.warning("No data to save")
            return None
        
        """
        NOTE: For production we avoid keeping historical timestamped files to
        prevent unbounded disk growth. This method is kept for ad‑hoc local use,
        but is no longer called from the monitoring loop.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{filename_prefix}_{self.market_type.lower()}_{timestamp}.json"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Data saved to: {filepath}")
            logger.info(f"   Total records: {data['metadata']['total_records']}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving JSON: {e}")
            return None
    
    def save_latest(self, data):
        """Save data as 'latest.json' for easy access"""
        if not data:
            return None
        
        filepath = os.path.join(self.output_dir, f'latest_{self.market_type.lower()}.json')
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Updated latest_{self.market_type.lower()}.json")
            return filepath
            
        except Exception as e:
            logger.error(f"Error saving latest.json: {e}")
            return None

    def cleanup_old_files(self):
        """Delete historical JSON files keeping only latest_*.json.

        This prevents the monitor from filling up disk over time when running
        continuously in production.
        """
        try:
            for filename in os.listdir(self.output_dir):
                if not filename.lower().endswith(".json"):
                    continue
                # Keep only latest_*.json files
                if filename.startswith(f"latest_{self.market_type.lower()}"):
                    continue
                full_path = os.path.join(self.output_dir, filename)
                try:
                    os.remove(full_path)
                    logger.info(f"Deleted old file: {full_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete {full_path}: {e}")
    
    def run_single_scrape(self, max_pages=None):
        """Run a single scrape operation"""
        logger.info("=" * 80)
        logger.info(f"Starting scheduled scrape for {self.market_type}...")
        logger.info("=" * 80)
        
        try:
            # Scrape data
            data = self.scrape_all_pages(max_pages=max_pages)
            
            if data:
                # Save only the latest snapshot used by the API
                self.save_latest(data)
                # Cleanup any historical files left from previous runs
                self.cleanup_old_files()
                
                # Store for comparison
                self.last_data = data
                
                logger.info("✅ Scrape completed successfully")
                
                return data
            else:
                logger.warning("⚠️ Scrape returned no data")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error during scrape: {e}")
            
            # Try to reinitialize driver
            logger.info("Attempting to reinitialize driver...")
            self._init_driver()
            
            return None
    
    def start_monitoring(self, interval_minutes=5, max_pages=None):
        """
        Start continuous monitoring with scheduled scraping
        
        Args:
            interval_minutes (int): Interval between scrapes in minutes
            max_pages (int): Maximum pages to scrape per run (None for all)
        """
        logger.info("=" * 80)
        logger.info("NSE ANNOUNCEMENTS MONITOR")
        logger.info("=" * 80)
        logger.info(f"URL: {self.url}")
        logger.info(f"Market Type: {self.market_type}")
        logger.info(f"Interval: Every {interval_minutes} minutes")
        logger.info(f"Output: {self.output_dir}/")
        logger.info(f"Mode: {'Headless' if self.headless else 'Visible'}")
        if max_pages:
            logger.info(f"Max Pages: {max_pages} per scrape")
        logger.info("=" * 80)
        
        # Initialize driver
        if not self._init_driver():
            logger.error("Failed to initialize driver. Exiting...")
            return
        
        # Run first scrape immediately
        logger.info("\n🚀 Running initial scrape...")
        self.run_single_scrape(max_pages=max_pages)
        
        # Schedule periodic scraping
        schedule.every(interval_minutes).minutes.do(lambda: self.run_single_scrape(max_pages=max_pages))
        
        logger.info(f"\n✅ Monitor started! Scraping every {interval_minutes} minutes.")
        logger.info("Press Ctrl+C to stop.\n")
        
        # Keep running
        try:
            while True:
                schedule.run_pending()
                time.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            logger.info("\n\n⏹️  Monitor stopped by user")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """Cleanup resources"""
        logger.info("Cleaning up...")
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed")
            except:
                pass


def main():
    """Main execution function"""
    print("\n" + "=" * 80)
    print("NSE ANNOUNCEMENTS MONITOR")
    print("=" * 80)
    print("\nThis script will scrape the NSE Announcements page every 5 minutes")
    print("and save the data in JSON format.\n")
    
    # Ask for market type
    print("Available Market Types:")
    print("  1. Equity (default)")
    print("  2. SME")
    print("  3. Debt")
    print("  4. MF (Mutual Funds)")
    print("  5. REIT/InvIT")
    print("  6. Municipal Bond")
    print("  7. SSE")
    print("  8. DT Disclosures")
    
    market_choice = input("\nSelect market type (1-8, default: 1): ").strip()
    
    market_types = {
        '1': 'Equity',
        '2': 'SME',
        '3': 'Debt',
        '4': 'MF',
        '5': 'REIT/InvIT',
        '6': 'Municipal Bond',
        '7': 'SSE',
        '8': 'DT Disclosures'
    }
    
    market_type = market_types.get(market_choice, 'Equity')
    
    # Ask for max pages (to limit scraping)
    max_pages_input = input("\nLimit pages per scrape (press Enter for all pages): ").strip()
    max_pages = int(max_pages_input) if max_pages_input.isdigit() else None
    
    # Ask for headless mode
    headless_input = input("Run in headless mode? (y/n, default: y): ").strip().lower()
    headless = headless_input != 'n'
    
    print("\nConfiguration:")
    print(f"  - Market Type: {market_type}")
    print(f"  - Interval: 5 minutes")
    print(f"  - Format: JSON")
    print(f"  - Output: announcements_data/")
    print(f"  - Latest data: announcements_data/latest_{market_type.lower()}.json")
    if max_pages:
        print(f"  - Max Pages: {max_pages}")
    print()
    
    # Create monitor
    monitor = AnnouncementsMonitor(
        headless=headless,
        market_type=market_type
    )
    
    # Start monitoring
    try:
        monitor.start_monitoring(interval_minutes=5, max_pages=max_pages)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        monitor.cleanup()


if __name__ == "__main__":
    main()

