"""
Groww Stock News Scraper
========================

Scraper for Groww's "Stocks in news" section that extracts:
- News source and time
- News headline
- Related stock name and percentage change

Usage:
    python groww_stock_news_scraper.py
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
import re

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GrowwStockNewsScraper:
    """Scraper for Groww Stock News section"""
    
    def __init__(self, headless=False):
        """Initialize the scraper"""
        self.url = "https://groww.in/share-market-today"
        self.headless = headless
        self.driver = None
        self.wait = None
    
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
        """Navigate to Groww share market page"""
        try:
            logger.info(f"Navigating to: {self.url}")
            self.driver.get(self.url)
            
            # Wait for page to load
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            logger.info("Initial page load complete")
            
            # Wait for JavaScript to execute and content to load
            time.sleep(5)
            
            # Scroll down gradually to trigger lazy loading
            logger.info("Scrolling to load content...")
            scroll_pause = 1
            scroll_height = self.driver.execute_script("return document.body.scrollHeight")
            current_position = 0
            scroll_step = 500
            
            while current_position < scroll_height:
                self.driver.execute_script(f"window.scrollTo(0, {current_position});")
                time.sleep(scroll_pause)
                current_position += scroll_step
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height > scroll_height:
                    scroll_height = new_height
            
            # Scroll back up a bit and wait for content to settle
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(3)
            
            # Try to wait for news-related elements
            try:
                # Wait for any element that might indicate news section
                self.wait.until(
                    EC.any_of(
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'ago')]")),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'CNBC')]")),
                        EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Business Standard')]"))
                    )
                )
                logger.info("News content detected on page")
            except TimeoutException:
                logger.warning("Timeout waiting for news content, but continuing...")
            
            logger.info("Page loaded and scrolled successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading page: {e}")
            return False
    
    def find_news_section(self):
        """
        Find the 'Stocks in news' section container
        
        Returns:
            WebElement or None: The container element containing news items
        """
        try:
            logger.info("Searching for 'Stocks in news' section...")
            
            # Method 1: Look for heading containing "Stocks in news"
            try:
                # Try multiple variations of the heading text
                heading_patterns = [
                    "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'stocks in news')]",
                    "//*[contains(text(), 'Stocks in news')]",
                    "//*[contains(text(), 'Stocks in News')]",
                    "//h2[contains(text(), 'news')]",
                    "//h3[contains(text(), 'news')]",
                    "//*[@class and contains(translate(@class, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'news')]"
                ]
                
                for pattern in heading_patterns:
                    try:
                        headings = self.driver.find_elements(By.XPATH, pattern)
                        
                        for heading in headings:
                            try:
                                text = heading.text.strip().lower()
                                if 'stocks' in text and 'news' in text:
                                    # Find the parent container - look for a div that contains multiple news items
                                    # Try to find a container that has multiple time elements
                                    for i in range(1, 10):
                                        try:
                                            container = heading.find_element(By.XPATH, f"./ancestor::*[position()={i}]")
                                            # Check if this container has multiple news items
                                            time_elements = container.find_elements(
                                                By.XPATH,
                                                ".//*[contains(text(), 'ago')]"
                                            )
                                            if len(time_elements) >= 2:
                                                logger.info("Found news section via heading")
                                                return container
                                        except:
                                            continue
                            except:
                                continue
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Method 1 (heading search) failed: {e}")
            
            # Method 2: Look for elements containing news source patterns (CNBC, Business Standard, etc.)
            try:
                news_sources = ['CNBC TV18', 'Business Standard', 'The Hindu', 'Economic Times', 'News18', 'Zee Business']
                
                for source in news_sources:
                    try:
                        elements = self.driver.find_elements(
                            By.XPATH, 
                            f"//*[contains(text(), '{source}')]"
                        )
                        
                        if elements:
                            # Find common parent container that contains multiple news items
                            for element in elements:
                                try:
                                    # Try different ancestor levels
                                    for level in range(3, 10):
                                        try:
                                            parent = element.find_element(By.XPATH, f"./ancestor::*[position()={level}]")
                                            
                                            # Check if this parent has multiple news-like elements
                                            time_children = parent.find_elements(
                                                By.XPATH,
                                                ".//*[contains(text(), 'ago')]"
                                            )
                                            
                                            if len(time_children) >= 3:  # Likely a news container
                                                logger.info(f"Found news section via source pattern: {source}")
                                                return parent
                                        except:
                                            continue
                                except:
                                    continue
                    except:
                        continue
            except Exception as e:
                logger.debug(f"Method 2 (source pattern) failed: {e}")
            
            # Method 3: Look for time patterns and find their common container
            try:
                time_elements = self.driver.find_elements(
                    By.XPATH,
                    "//*[contains(text(), 'ago') and (contains(text(), 'hour') or contains(text(), 'minute'))]"
                )
                
                if time_elements and len(time_elements) >= 2:
                    # Get common ancestor of first few time elements
                    try:
                        # Get first time element's ancestors
                        first_ancestors = []
                        for i in range(1, 10):
                            try:
                                ancestor = time_elements[0].find_element(By.XPATH, f"./ancestor::*[position()={i}]")
                                first_ancestors.append(ancestor)
                            except:
                                break
                        
                        # Check which ancestor contains multiple time elements
                        for ancestor in reversed(first_ancestors):  # Start from deeper ancestors
                            time_count = ancestor.find_elements(
                                By.XPATH,
                                ".//*[contains(text(), 'ago')]"
                            )
                            if len(time_count) >= 2:
                                logger.info("Found news section via time pattern")
                                return ancestor
                    except:
                        pass
                    
                    # Fallback: return first time element's parent
                    first_time = time_elements[0]
                    container = first_time.find_element(By.XPATH, "./ancestor::*[position()<=8]")
                    logger.info("Found news section via time pattern (fallback)")
                    return container
            except Exception as e:
                logger.debug(f"Method 3 (time pattern) failed: {e}")
            
            logger.warning("Could not find news section container, will try to scrape all news items directly")
            return None
            
        except Exception as e:
            logger.error(f"Error finding news section: {e}")
            return None
    
    def scrape_news_items(self, container=None):
        """
        Scrape all news items from the page
        
        Args:
            container: Optional container element to limit search scope
        
        Returns:
            list: List of news item dictionaries
        """
        try:
            logger.info("Scraping news items...")
            
            news_items = []
            
            # If container is provided, search within it, otherwise search entire page
            search_root = container if container else self.driver
            
            # Debug: Check what's actually on the page
            try:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text
                if 'ago' in page_text.lower():
                    logger.info("Found 'ago' text in page content")
                if 'CNBC' in page_text or 'Business Standard' in page_text:
                    logger.info("Found news sources in page content")
            except:
                pass
            
            # Method 1: Look for elements containing "ago" (time pattern)
            try:
                # Try multiple XPath patterns to find time elements
                time_patterns = [
                    ".//*[contains(text(), 'ago')]",
                    ".//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'ago')]",
                ]
                
                time_elements = []
                for pattern in time_patterns:
                    try:
                        elements = search_root.find_elements(By.XPATH, pattern)
                        if elements:
                            time_elements = elements
                            logger.info(f"Found {len(elements)} elements with time patterns")
                            break
                    except:
                        continue
                
                if not time_elements:
                    # Try finding by partial text match (limited search)
                    logger.info("Trying alternative method to find time elements...")
                    all_elements = search_root.find_elements(By.XPATH, ".//*")
                    checked = 0
                    for elem in all_elements:
                        if checked > 500:  # Limit search
                            break
                        checked += 1
                        try:
                            text = elem.text or ""
                            if 'ago' in text.lower() and ('hour' in text.lower() or 'minute' in text.lower()):
                                time_elements.append(elem)
                                if len(time_elements) >= 20:  # Limit to 20
                                    break
                        except:
                            continue
                    logger.info(f"Found {len(time_elements)} elements with time patterns (alternative method)")
                
                processed_containers = set()
                logger.info(f"Processing {len(time_elements)} time elements...")
                
                for idx, time_element in enumerate(time_elements[:30], 1):  # Limit to first 30
                    if idx % 5 == 0:
                        logger.info(f"Processing time element {idx}/{min(len(time_elements), 30)}...")
                    
                    try:
                        # Get the parent container that should contain the full news item
                        # Try different ancestor levels
                        extracted = False
                        for level in range(4, 7):  # Reduced range
                            try:
                                parent = time_element.find_element(By.XPATH, f"./ancestor::*[position()={level}]")
                                
                                # Get a unique identifier for this container
                                try:
                                    container_id = parent.get_attribute('outerHTML')[:200] if parent else str(id(parent))
                                except:
                                    container_id = str(id(parent))
                                
                                if container_id in processed_containers:
                                    continue
                                
                                # Check if this container looks like a news item container
                                container_text = parent.text if parent else ""
                                if len(container_text) > 50 and ('%' in container_text or '₹' in container_text):
                                    processed_containers.add(container_id)
                                    
                                    # Extract news data from this container
                                    news_data = self._extract_news_from_container(parent)
                                    
                                    if news_data and news_data.get('headline'):
                                        headline = news_data.get('headline', '')
                                        # Validate headline
                                        if len(headline) > 20 and headline.lower() not in ['no data available for this category', 'see more', 'view more']:
                                            # Check if we already have this headline
                                            if not any(item.get('headline', '').lower() == headline.lower() for item in news_items):
                                                news_items.append(news_data)
                                                logger.info(f"✓ Extracted news {len(news_items)}: {headline[:60]}... | Stock: {news_data.get('stock_name', 'N/A')} {news_data.get('stock_change', 'N/A')}")
                                                extracted = True
                                                break
                            except:
                                continue
                        
                        # Early exit if we have enough items
                        if len(news_items) >= 15:
                            logger.info(f"Found {len(news_items)} news items, stopping early...")
                            break
                    
                    except Exception as e:
                        logger.debug(f"Error processing time element {idx}: {e}")
                        continue
                
                logger.info(f"Method 1 completed: extracted {len(news_items)} news items")
                
            except Exception as e:
                logger.warning(f"Method 1 failed: {e}")
            
            # Method 2: Look for links that contain stock percentage (these are part of news items)
            # Only run if we haven't found enough items yet
            if len(news_items) < 10:
                try:
                    logger.info("Trying alternative method: searching for stock links...")
                    
                    # Try multiple patterns for stock links
                    link_patterns = [
                        ".//a[contains(text(), '%')]",
                        ".//*[self::a or self::button][contains(text(), '%')]",
                        ".//*[@href and contains(text(), '%')]",
                    ]
                    
                    stock_links = []
                    for pattern in link_patterns:
                        try:
                            links = search_root.find_elements(By.XPATH, pattern)
                            if links:
                                stock_links = links
                                logger.info(f"Found {len(links)} stock links using pattern: {pattern}")
                                break
                        except:
                            continue
                    
                    # If no links found, try finding any element with percentage
                    if not stock_links:
                        all_elements = search_root.find_elements(By.XPATH, ".//*")
                        for elem in all_elements:
                            try:
                                text = elem.text or ""
                                if '%' in text and any(char.isdigit() for char in text):
                                    stock_links.append(elem)
                            except:
                                continue
                        logger.info(f"Found {len(stock_links)} elements with percentage (alternative method)")
                    
                    processed_links = set()
                    processed_containers = set()
                    total_links = len(stock_links)
                    logger.info(f"Processing {total_links} stock elements...")
                    
                    # Limit processing to first 50 most promising elements to avoid timeout
                    # Filter elements that look like stock info (not just random percentages)
                    promising_links = []
                    for link in stock_links[:100]:  # Check first 100
                        try:
                            link_text = link.text or ""
                            # Skip if too long (likely not stock info)
                            if len(link_text) > 60 or len(link_text) < 5:
                                continue
                            # Skip if contains "ago" (it's source/time)
                            if 'ago' in link_text.lower():
                                continue
                            # Must have percentage and some letters (stock name)
                            if '%' in link_text and any(char.isalpha() for char in link_text):
                                promising_links.append(link)
                                if len(promising_links) >= 30:  # Limit to 30 most promising
                                    break
                        except:
                            continue
                    
                    logger.info(f"Found {len(promising_links)} promising stock elements to process")
                    
                    for idx, link in enumerate(promising_links, 1):
                        try:
                            if idx % 5 == 0:
                                logger.info(f"Processing element {idx}/{len(promising_links)}...")
                            
                            link_text = link.text or ""
                            if link_text in processed_links:
                                continue
                            processed_links.add(link_text)
                            
                            # Get parent container - try different levels
                            extracted = False
                            for level in range(4, 7):  # Reduced range for speed
                                try:
                                    parent = link.find_element(By.XPATH, f"./ancestor::*[position()={level}]")
                                    
                                    # Skip if we've already processed this container
                                    try:
                                        container_id = parent.get_attribute('outerHTML')[:200] if parent else str(id(parent))
                                    except:
                                        container_id = str(id(parent))
                                    
                                    if container_id in processed_containers:
                                        continue
                                    processed_containers.add(container_id)
                                    
                                    news_data = self._extract_news_from_container(parent)
                                    
                                    if news_data and news_data.get('headline'):
                                        headline = news_data.get('headline', '')
                                        # Validate headline
                                        if len(headline) > 20 and headline.lower() not in ['no data available for this category', 'see more', 'view more']:
                                            # Check for duplicates
                                            if not any(item.get('headline', '').lower() == headline.lower() for item in news_items):
                                                news_items.append(news_data)
                                                logger.info(f"✓ Extracted news {len(news_items)}: {headline[:60]}... | Stock: {news_data.get('stock_name', 'N/A')} {news_data.get('stock_change', 'N/A')}")
                                                extracted = True
                                                break
                                except Exception as e:
                                    continue
                            
                            # If we've found enough items, we can stop early
                            if len(news_items) >= 15:
                                logger.info(f"Found {len(news_items)} news items, stopping early...")
                                break
                                
                        except Exception as e:
                            logger.debug(f"Error processing link {idx}: {e}")
                            continue
                    
                    logger.info(f"Method 2 completed: extracted {len(news_items)} news items")
                
                except Exception as e:
                    logger.warning(f"Method 2 failed: {e}")
            
            # Method 3: Try to find news items by looking for common news source names
            # Only run if we haven't found enough items yet
            if len(news_items) < 10:
                try:
                    logger.info("Trying method 3: searching by news sources...")
                    news_sources = ['CNBC', 'Business Standard', 'The Hindu', 'Economic Times', 'News18', 'Zee Business']
                    
                    for source in news_sources:
                        try:
                            source_elements = search_root.find_elements(
                                By.XPATH,
                                f".//*[contains(text(), '{source}')]"
                            )
                            
                            for source_elem in source_elements:
                                try:
                                    # Get parent container
                                    for level in range(2, 7):
                                        try:
                                            parent = source_elem.find_element(By.XPATH, f"./ancestor::*[position()={level}]")
                                            news_data = self._extract_news_from_container(parent)
                                            
                                            if news_data and news_data.get('headline'):
                                                if not any(item.get('headline', '').lower() == news_data.get('headline', '').lower() for item in news_items):
                                                    news_items.append(news_data)
                                                    logger.debug(f"Extracted news from source: {news_data.get('headline', '')[:50]}...")
                                                    break
                                        except:
                                            continue
                                except:
                                    continue
                        except:
                            continue
                except Exception as e:
                    logger.warning(f"Method 3 failed: {e}")
            
            # Remove duplicates based on headline
            unique_items = []
            seen_headlines = set()
            
            for item in news_items:
                headline_key = item.get('headline', '').lower().strip()
                if headline_key and headline_key not in seen_headlines and len(headline_key) > 10:
                    seen_headlines.add(headline_key)
                    unique_items.append(item)
            
            logger.info(f"Scraped {len(unique_items)} unique news items")
            
            # Log summary of extracted items
            if unique_items:
                logger.info("=" * 60)
                logger.info("EXTRACTION SUMMARY:")
                logger.info("=" * 60)
                for i, item in enumerate(unique_items[:5], 1):
                    logger.info(f"{i}. {item.get('source', 'N/A')} | {item.get('headline', 'N/A')[:50]}...")
                    logger.info(f"   Stock: {item.get('stock_name', 'N/A')} {item.get('stock_change', 'N/A')}")
                if len(unique_items) > 5:
                    logger.info(f"... and {len(unique_items) - 5} more items")
                logger.info("=" * 60)
            
            return unique_items
            
        except Exception as e:
            logger.error(f"Error scraping news items: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _extract_stock_info_from_element(self, element):
        """
        Extract stock name and percentage from an element
        
        Args:
            element: WebElement that should contain stock info
        
        Returns:
            tuple: (stock_name, stock_change) or (None, None)
        """
        try:
            text = element.text.strip() if element else ""
            if not text or '%' not in text:
                return None, None
            
            # Patterns to match stock info
            patterns = [
                re.compile(r'^([A-Za-z][A-Za-z\s&.,()]+?)\s+([-+]?\d+\.\d+%)$', re.IGNORECASE),  # Full match
                re.compile(r'([A-Za-z][A-Za-z\s&.,()]+?)\s+([-+]?\d+\.\d+%)', re.IGNORECASE),   # Partial match
                re.compile(r'([A-Za-z][A-Za-z\s&.,()]+?)\s+([-+]?\d+%)', re.IGNORECASE),        # Without decimal
            ]
            
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    stock_name = match.group(1).strip()
                    stock_change = match.group(2).strip()
                    # Validate
                    if stock_name and len(stock_name) > 1 and len(stock_name) < 50 and stock_name != '.':
                        if stock_change and len(stock_change) >= 4:  # At least "1.0%"
                            return stock_name, stock_change
            
            # Fallback: extract percentage and name separately
            pct_match = re.search(r'([-+]?\d+\.\d+%)', text)
            if pct_match:
                stock_change = pct_match.group(1)
                name_part = text[:pct_match.start()].strip()
                name_part = re.sub(r'[.,\s]+$', '', name_part)
                if name_part and len(name_part) > 1 and len(name_part) < 50 and name_part != '.':
                    return name_part, stock_change
            
            return None, None
        except:
            return None, None
    
    def _extract_news_from_container(self, container):
        """
        Extract news data from a container element that contains a full news item
        
        Args:
            container: WebElement container that should have:
                - Child with source/time
                - Child with headline
                - Link with stock info
        
        Returns:
            dict or None: News data dictionary
        """
        try:
            news_data = {
                'source': '',
                'time': '',
                'headline': '',
                'stock_name': '',
                'stock_change': ''
            }
            
            # Get full text from container
            container_text = container.text if container else ""
            
            if not container_text or len(container_text) < 20:
                return None
            
            # Split into lines for analysis
            lines = [line.strip() for line in container_text.split('\n') if line.strip()]
            
            if len(lines) < 2:
                return None
            
            # Method 1: Find source/time (contains "ago")
            try:
                time_pattern = re.compile(r'(\d+\s*(?:hour|minute|day)s?\s*ago)', re.IGNORECASE)
                
                # Look through lines for time pattern
                for line in lines:
                    if 'ago' in line.lower():
                        # Parse "Source - X hours ago" or "Source · X hours ago" or "Source X hours ago"
                        # Try "-" separator first (most common based on image)
                        if ' - ' in line or line.count('-') == 1:
                            parts = line.split('-', 1)
                            if len(parts) >= 2:
                                news_data['source'] = parts[0].strip()
                                time_part = parts[1].strip()
                                time_match = time_pattern.search(time_part)
                                if time_match:
                                    news_data['time'] = time_match.group(1)
                        elif '·' in line:
                            parts = line.split('·')
                            if len(parts) >= 2:
                                news_data['source'] = parts[0].strip()
                                time_part = parts[1].strip()
                                time_match = time_pattern.search(time_part)
                                if time_match:
                                    news_data['time'] = time_match.group(1)
                        else:
                            # Try to extract time and source from same line
                            time_match = time_pattern.search(line)
                            if time_match:
                                news_data['time'] = time_match.group(1)
                                # Source is everything before time
                                source_part = line[:time_match.start()].strip()
                                # Remove common separators
                                news_data['source'] = source_part.replace('·', '').replace('-', '').strip()
                        break
            except Exception as e:
                logger.debug(f"Error extracting source/time: {e}")
            
            # Method 2: Find headline (longest line that's not source/time or stock info)
            try:
                for line in lines:
                    # Skip if it's source/time or stock info
                    if 'ago' in line.lower() or '%' in line:
                        continue
                    
                    # Skip very short lines
                    if len(line) < 30:
                        continue
                    
                    # Skip if it looks like navigation or UI text
                    if any(skip in line.lower() for skip in ['see more', 'view more', 'login', 'sign up', 'search']):
                        continue
                    
                    # This is likely the headline
                    if len(line) > len(news_data.get('headline', '')):
                        news_data['headline'] = line
            except Exception as e:
                logger.debug(f"Error extracting headline: {e}")
            
            # Method 3: Find stock info (contains "%")
            try:
                # Improved pattern: Stock name (letters, spaces, common punctuation) followed by percentage
                # Pattern should match: "Godrej Properties 1.04%" or "SBI -0.01%"
                # Use more flexible pattern that handles various formats
                stock_pattern_full = re.compile(r'([A-Za-z][A-Za-z\s&.,()]+?)\s+([-+]?\d+\.\d+%)', re.IGNORECASE)
                stock_pattern_simple = re.compile(r'([A-Za-z][A-Za-z\s&.,()]+?)\s+([-+]?\d+%)', re.IGNORECASE)
                pct_pattern = re.compile(r'([-+]?\d+\.\d+%)', re.IGNORECASE)
                
                # First try to find in links/buttons (stock info is usually in a clickable element)
                try:
                    # Try multiple selectors for stock info elements
                    stock_selectors = [
                        ".//a[contains(text(), '%')]",
                        ".//*[@href and contains(text(), '%')]",
                        ".//button[contains(text(), '%')]",
                        ".//*[contains(@class, 'button') and contains(text(), '%')]",
                        ".//*[contains(@class, 'stock') and contains(text(), '%')]",
                        ".//*[contains(@class, 'link') and contains(text(), '%')]",
                        ".//*[@role='link' and contains(text(), '%')]",
                    ]
                    
                    stock_elements = []
                    for selector in stock_selectors:
                        try:
                            elements = container.find_elements(By.XPATH, selector)
                            if elements:
                                stock_elements.extend(elements)
                        except:
                            continue
                    
                    # Also try finding by text pattern directly
                    if not stock_elements:
                        all_elements = container.find_elements(By.XPATH, ".//*")
                        for elem in all_elements:
                            try:
                                text = elem.text or ""
                                # Look for elements with percentage that are likely stock info
                                if '%' in text and len(text) > 5 and len(text) < 60:
                                    # Check if it has a stock-like pattern
                                    if pct_pattern.search(text) and any(char.isalpha() for char in text):
                                        stock_elements.append(elem)
                            except:
                                continue
                    
                    if stock_elements:
                        for elem in stock_elements:
                            stock_text = elem.text.strip()
                            # Skip if it's too short or too long
                            if len(stock_text) < 5 or len(stock_text) > 60:
                                continue
                            
                            # Skip if it contains "ago" (it's source/time, not stock)
                            if 'ago' in stock_text.lower():
                                continue
                            
                            # Use the dedicated extraction method
                            stock_name, stock_change = self._extract_stock_info_from_element(elem)
                            if stock_name and stock_change:
                                news_data['stock_name'] = stock_name
                                news_data['stock_change'] = stock_change
                                break
                except Exception as e:
                    logger.debug(f"Error finding stock elements: {e}")
                
                # If not found in links, search in all text lines
                if not news_data['stock_name'] or news_data['stock_name'] == '.':
                    for line in lines:
                        if '%' in line and len(line) < 100:  # Stock info line is usually short
                            # Skip if it looks like headline or source
                            if 'ago' in line.lower() or len(line) > 80:
                                continue
                            
                            # Try pattern match
                            stock_match = stock_pattern.search(line)
                            if stock_match:
                                stock_name = stock_match.group(1).strip()
                                stock_change = stock_match.group(2).strip()
                                # Validate stock name (should be reasonable length)
                                if len(stock_name) > 1 and len(stock_name) < 50 and stock_name != '.':
                                    news_data['stock_name'] = stock_name
                                    news_data['stock_change'] = stock_change
                                    break
                            
                            # Fallback: extract percentage and name separately
                            pct_match = re.search(r'([-+]?\d+\.\d+%)', line)
                            if pct_match:
                                news_data['stock_change'] = pct_match.group(1)
                                # Stock name is everything before percentage
                                name_part = line[:pct_match.start()].strip()
                                # Clean up
                                name_part = re.sub(r'[.,\s]+$', '', name_part)
                                if name_part and len(name_part) > 1 and len(name_part) < 50 and name_part != '.':
                                    news_data['stock_name'] = name_part
                                    break
            except Exception as e:
                logger.debug(f"Error extracting stock info: {e}")
            
            # Clean up stock name - remove invalid values
            if news_data['stock_name'] in ['.', '', ' ', '..']:
                news_data['stock_name'] = ''
            
            # Clean up stock change - ensure it's a valid percentage
            if news_data['stock_change']:
                # Remove invalid partial percentages like "00%", "01%" that are likely errors
                if re.match(r'^0+%$', news_data['stock_change']) or len(news_data['stock_change']) < 4:
                    # Try to find the actual percentage in the container
                    pct_match = re.search(r'([-+]?\d+\.\d+%)', container_text)
                    if pct_match:
                        news_data['stock_change'] = pct_match.group(1)
                    else:
                        news_data['stock_change'] = ''
            
            # Validate: must have at least headline
            if news_data['headline'] and len(news_data['headline']) > 20:
                # Filter out invalid headlines
                if news_data['headline'].lower() not in ['no data available for this category', 'see more', 'view more']:
                    return news_data
            
            # Alternative validation: if we have source/time, try to get headline from container structure
            if news_data['source'] or news_data['time']:
                # Try to find headline by looking at child elements
                try:
                    children = container.find_elements(By.XPATH, ".//*")
                    for child in children:
                        try:
                            child_text = child.text.strip()
                            # Skip if it's source/time or stock
                            if 'ago' in child_text.lower() or '%' in child_text or len(child_text) < 30:
                                continue
                            # Skip UI elements
                            if any(skip in child_text.lower() for skip in ['see more', 'view more', 'login', 'no data available']):
                                continue
                            
                            if len(child_text) > len(news_data.get('headline', '')):
                                news_data['headline'] = child_text
                        except:
                            continue
                    
                    if news_data['headline'] and len(news_data['headline']) > 20:
                        # Filter out invalid headlines
                        if news_data['headline'].lower() not in ['no data available for this category', 'see more', 'view more']:
                            return news_data
                except:
                    pass
            
            return None
            
        except Exception as e:
            logger.debug(f"Error extracting news from container: {e}")
            return None
    
    def debug_page_content(self):
        """Debug method to inspect what's actually on the page"""
        try:
            logger.info("=== DEBUG: Page Content Analysis ===")
            
            # Get page source length
            page_source = self.driver.page_source
            logger.info(f"Page source length: {len(page_source)} characters")
            
            # Check for key terms in page source
            key_terms = ['ago', 'CNBC', 'Business Standard', 'news', 'Stocks in news']
            for term in key_terms:
                count = page_source.lower().count(term.lower())
                logger.info(f"Found '{term}' {count} times in page source")
            
            # Get body text
            try:
                body_text = self.driver.find_element(By.TAG_NAME, "body").text
                logger.info(f"Body text length: {len(body_text)} characters")
                
                # Check for key terms in visible text
                for term in key_terms:
                    count = body_text.lower().count(term.lower())
                    logger.info(f"Found '{term}' {count} times in visible text")
                
                # Show first 500 chars of body text
                logger.info(f"First 500 chars of body text:\n{body_text[:500]}")
            except Exception as e:
                logger.error(f"Error getting body text: {e}")
            
            # Try to find any elements with "ago"
            try:
                ago_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'ago')]")
                logger.info(f"Found {len(ago_elements)} elements containing 'ago'")
                for i, elem in enumerate(ago_elements[:5], 1):
                    try:
                        logger.info(f"  {i}. Text: {elem.text[:100]}")
                        logger.info(f"     Tag: {elem.tag_name}, Class: {elem.get_attribute('class')}")
                    except:
                        pass
            except Exception as e:
                logger.error(f"Error finding 'ago' elements: {e}")
            
            logger.info("=== END DEBUG ===")
            
        except Exception as e:
            logger.error(f"Error in debug_page_content: {e}")
    
    def scrape_all_news(self):
        """
        Main method to scrape all stock news
        
        Returns:
            dict: Dictionary containing all scraped news items
        """
        try:
            # Debug page content if no items found initially
            logger.info("Starting news scraping...")
            
            # Find news section container
            container = self.find_news_section()
            
            # Scrape news items
            news_items = self.scrape_news_items(container)
            
            # If no items found, run debug
            if len(news_items) == 0:
                logger.warning("No news items found, running debug analysis...")
                self.debug_page_content()
            
            result = {
                'scrape_timestamp': datetime.now().isoformat(),
                'url': self.url,
                'total_news_items': len(news_items),
                'news_items': news_items
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in scrape_all_news: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def save_data(self, data, filename="groww_stock_news"):
        """Save data to JSON file.

        To avoid unbounded disk growth we now keep only a single "latest"
        snapshot by default instead of timestamped files. If you need
        historical files locally, change the filename argument when calling.
        """
        try:
            # Default behaviour: single rolling file
            filepath = f"{filename}_latest.json"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Data saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error saving data: {e}")
            return None
    
    def take_screenshot(self, filename="groww_news_debug"):
        """Take screenshot of current page"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filepath = f"{filename}_{timestamp}.png"
            self.driver.save_screenshot(filepath)
            logger.info(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Error taking screenshot: {e}")
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
    """Main function"""
    print("\n" + "=" * 80)
    print("GROWW STOCK NEWS SCRAPER")
    print("=" * 80)
    
    # Ask for headless mode
    headless_input = input("\nRun in headless mode? (y/n, default: n): ").strip().lower()
    headless = headless_input == 'y'
    
    # Initialize scraper
    scraper = GrowwStockNewsScraper(headless=headless)
    
    try:
        # Initialize driver
        if not scraper._init_driver():
            print("❌ Failed to initialize browser")
            return
        
        # Navigate to page
        if not scraper.navigate_to_page():
            print("❌ Failed to load page")
            return
        
        print("\n✅ Page loaded successfully")
        print("Scraping stock news...")
        
        # Scrape all news
        news_data = scraper.scrape_all_news()
        
        if news_data and news_data.get('news_items'):
            # Save data
            filepath = scraper.save_data(news_data)
            
            print(f"\n✅ Scraping completed successfully!")
            print(f"   Total news items: {news_data['total_news_items']}")
            print(f"   Data saved to: {filepath}")
            
            # Display first few items
            print("\n" + "-" * 80)
            print("SAMPLE NEWS ITEMS:")
            print("-" * 80)
            
            for i, item in enumerate(news_data['news_items'][:5], 1):
                print(f"\n{i}. {item.get('source', 'Unknown')} · {item.get('time', 'Unknown time')}")
                print(f"   Headline: {item.get('headline', 'N/A')}")
                print(f"   Stock: {item.get('stock_name', 'N/A')} ({item.get('stock_change', 'N/A')})")
            
            if len(news_data['news_items']) > 5:
                print(f"\n... and {len(news_data['news_items']) - 5} more items")
        else:
            print("\n⚠️  No news items found")
            print("Taking screenshot for debugging...")
            scraper.take_screenshot()
        
        # Wait before closing
        if not headless:
            input("\nPress Enter to close browser...")
    
    except KeyboardInterrupt:
        print("\n\n⏹️  Interrupted by user")
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        scraper.take_screenshot("groww_news_error")
    
    finally:
        scraper.cleanup()
    
    print("\n" + "=" * 80)
    print("SCRAPING COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    main()

