"""
NSE Heatmap API
===============

Professional REST API for NSE heatmap data.
Allows clients to:
1. Get available categories
2. Get indices for a category
3. Get heatmap data for any index

Endpoints:
    GET /                    - API documentation
    GET /health             - Health check
    GET /categories         - List all categories
    GET /indices            - List indices for a category
    GET /heatmap            - Get heatmap data for an index

Usage:
    python heatmap_api.py
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from datetime import datetime
import logging
import threading
import time

app = Flask(__name__)

# Enable CORS
CORS(app, 
     origins=["http://localhost:3000", "http://localhost:3001"],
     methods=["GET", "OPTIONS"],
     allow_headers=["Content-Type"],
     supports_credentials=False)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Thread-safe driver pool
driver_lock = threading.Lock()


class HeatmapService:
    """Service class for heatmap operations"""
    
    def __init__(self):
        self.url = "https://www.nseindia.com/market-data/live-market-indices/heatmap"
        self.categories = {
            'broad-market': 'Broad Market Indices',
            'sectoral': 'Sectoral Indices',
            'thematic': 'Thematic Indices',
            'strategy': 'Strategy Indices'
        }
        self.driver = None
    
    def _init_driver(self):
        """Initialize headless Chrome driver"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            return True
        except Exception as e:
            logger.error(f"Driver init failed: {e}")
            return False
    
    def _navigate_to_page(self):
        """Navigate to heatmap page"""
        try:
            self.driver.get(self.url)
            time.sleep(5)
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            return True
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return False
    
    def _select_category(self, category_key):
        """Select a category"""
        try:
            if category_key not in self.categories:
                return False
            
            category_name = self.categories[category_key]
            
            # Try multiple methods to find and click the category
            logger.info(f"Selecting category: {category_name}")
            
            # Method 1: Look for exact text match
            try:
                category_element = self.driver.find_element(
                    By.XPATH,
                    f"//div[text()='{category_name}'] | //a[text()='{category_name}'] | //button[text()='{category_name}']"
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", category_element)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", category_element)
                time.sleep(3)
                logger.info(f"Category selected successfully")
                return True
            except:
                pass
            
            # Method 2: Look for contains text
            try:
                category_element = self.driver.find_element(
                    By.XPATH,
                    f"//div[contains(text(), '{category_name}')] | //a[contains(text(), '{category_name}')] | //button[contains(text(), '{category_name}')]"
                )
                self.driver.execute_script("arguments[0].scrollIntoView(true);", category_element)
                time.sleep(0.5)
                self.driver.execute_script("arguments[0].click();", category_element)
                time.sleep(3)
                logger.info(f"Category selected successfully (method 2)")
                return True
            except:
                pass
            
            # Method 3: Try clickable elements with the category text
            try:
                clickable_elements = self.driver.find_elements(By.CSS_SELECTOR, "div, a, button, span")
                for elem in clickable_elements:
                    if category_name.lower() in elem.text.lower():
                        self.driver.execute_script("arguments[0].scrollIntoView(true);", elem)
                        time.sleep(0.5)
                        self.driver.execute_script("arguments[0].click();", elem)
                        time.sleep(3)
                        logger.info(f"Category selected successfully (method 3)")
                        return True
            except:
                pass
            
            logger.warning(f"Could not select category: {category_name}")
            return False
            
        except Exception as e:
            logger.error(f"Error selecting category: {e}")
            return False
    
    def get_indices(self, category_key):
        """Get all indices for a category"""
        try:
            with driver_lock:
                if not self.driver:
                    if not self._init_driver():
                        return None
                
                if not self._navigate_to_page():
                    return None
                
                # Select category and wait
                if not self._select_category(category_key):
                    logger.error(f"Failed to select category: {category_key}")
                    return None
                
                # Wait for content to load
                time.sleep(4)
                
                # Scroll down to load all cards
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
                time.sleep(2)
                
                # Find all index cards - try multiple selectors
                indices = []
                
                # Method 1: Look for clickable links with NIFTY
                cards = self.driver.find_elements(By.XPATH, "//a[contains(text(), 'NIFTY')]")
                
                for card in cards:
                    try:
                        card_text = card.text.strip()
                        if card_text and 'NIFTY' in card_text.upper():
                            lines = [l.strip() for l in card_text.split('\n') if l.strip()]
                            if lines and len(lines[0]) < 50:  # Reasonable index name length
                                indices.append({
                                    'name': lines[0],
                                    'value': lines[1] if len(lines) > 1 else '',
                                    'change': lines[2] if len(lines) > 2 else ''
                                })
                    except:
                        continue
                
                # Method 2: Look for div/spans with NIFTY text and find their parent clickable element
                if len(indices) == 0:
                    nifty_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'NIFTY')]")
                    
                    for elem in nifty_elements:
                        try:
                            # Find clickable parent
                            parent = elem.find_element(By.XPATH, "./ancestor::*[self::a or self::div[@onclick]][1]")
                            card_text = parent.text.strip()
                            
                            if card_text and 'NIFTY' in card_text.upper():
                                lines = [l.strip() for l in card_text.split('\n') if l.strip()]
                                if lines and len(lines[0]) < 50:
                                    indices.append({
                                        'name': lines[0],
                                        'value': lines[1] if len(lines) > 1 else '',
                                        'change': lines[2] if len(lines) > 2 else ''
                                    })
                        except:
                            continue
                
                # Remove duplicates
                seen = set()
                unique = []
                for idx in indices:
                    if idx['name'] not in seen:
                        seen.add(idx['name'])
                        unique.append(idx)
                
                logger.info(f"Found {len(unique)} indices for category {category_key}")
                return unique
                
        except Exception as e:
            logger.error(f"Error getting indices: {e}")
            return None
    
    def _click_sectoral_index(self, index_name):
        """
        Click on a sectoral/thematic/strategy index card.
        This method uses the working logic that successfully clicks sectoral indices.
        
        Returns:
            bool: True if successfully clicked and navigated to heatmap, False otherwise
        """
        try:
            logger.info(f"[SECTORAL] Clicking index: {index_name}")
            
            # Wait for content to load after category selection
            time.sleep(4)
            
            # Scroll to make sure cards are visible
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)
            
            # Clean up the index name for searching
            search_name = index_name.strip().upper()
            logger.info(f"[SECTORAL] Searching for index: '{search_name}'")
            
            clicked = False
            
            # Method 1: Look for exact text in clickable elements
            try:
                # Find all potential clickable elements
                all_clickables = self.driver.find_elements(By.CSS_SELECTOR, "a, div[onclick], button")
                
                logger.info(f"[SECTORAL] Found {len(all_clickables)} clickable elements")
                
                for card in all_clickables:
                    try:
                        card_text = card.text.strip()
                        if not card_text:
                            continue
                        
                        # Get first line (the index name)
                        first_line = card_text.split('\n')[0].strip().upper()
                        
                        # Check for match - exact or contains
                        is_match = (search_name == first_line or 
                                   search_name in first_line or
                                   first_line in search_name)
                        
                        if is_match:
                            logger.info(f"[SECTORAL] ✓ MATCH FOUND!")
                            logger.info(f"  Searching for: '{search_name}'")
                            logger.info(f"  Found card with: '{first_line}'")
                            logger.info(f"  Full text: {card_text[:100]}")
                            
                            # Try to extract JavaScript function
                            href = card.get_attribute('href')
                            onclick = card.get_attribute('onclick')
                            
                            logger.info(f"  href: {href}")
                            logger.info(f"  onclick: {onclick}")
                            
                            if href and 'javascript:' in href:
                                js_func = href.replace('javascript:', '')
                                logger.info(f"[SECTORAL] Executing JS from href...")
                                self.driver.execute_script(js_func)
                                time.sleep(5)
                                clicked = True
                                break
                            elif onclick:
                                logger.info(f"[SECTORAL] Executing onclick...")
                                self.driver.execute_script(onclick)
                                time.sleep(5)
                                clicked = True
                                break
                            else:
                                # Direct JavaScript click
                                logger.info(f"[SECTORAL] Using direct JavaScript click...")
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                                time.sleep(1)
                                self.driver.execute_script("arguments[0].click();", card)
                                time.sleep(5)
                                clicked = True
                                break
                    except Exception as e:
                        logger.debug(f"[SECTORAL] Error with card: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"[SECTORAL] Method 1 failed: {e}")
            
            if not clicked:
                # Method 2: Try finding by partial text match anywhere in the element
                logger.info("[SECTORAL] Method 1 failed, trying method 2...")
                try:
                    # Use XPath to find any element containing the index name
                    xpath = f"//*[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{search_name}')]"
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    
                    for elem in elements:
                        try:
                            # Find the clickable parent
                            clickable = elem.find_element(By.XPATH, "./ancestor-or-self::*[self::a or self::div[@onclick] or self::button][1]")
                            
                            if clickable:
                                logger.info(f"[SECTORAL] Found via XPath: {elem.text[:50]}")
                                href = clickable.get_attribute('href')
                                onclick = clickable.get_attribute('onclick')
                                
                                if href and 'javascript:' in href:
                                    js_func = href.replace('javascript:', '')
                                    self.driver.execute_script(js_func)
                                    time.sleep(5)
                                    clicked = True
                                    break
                                elif onclick:
                                    self.driver.execute_script(onclick)
                                    time.sleep(5)
                                    clicked = True
                                    break
                                else:
                                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable)
                                    time.sleep(1)
                                    self.driver.execute_script("arguments[0].click();", clickable)
                                    time.sleep(5)
                                    clicked = True
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.error(f"[SECTORAL] Method 2 failed: {e}")
            
            if not clicked:
                logger.error(f"[SECTORAL] Could not find or click index: {index_name}")
                return False
            
            # Verify we're on the heatmap page (not still on index list)
            time.sleep(3)
            try:
                # Check if we're on heatmap page by looking for heatmap-specific elements
                # Sectoral heatmap pages typically have stock tiles or heatmap containers
                heatmap_indicators = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "div[class*='heatmap'], div[id*='heatmap'], [class*='tile'], [class*='stock']"
                )
                if len(heatmap_indicators) > 0:
                    logger.info(f"[SECTORAL] ✓ Verified: Heatmap page loaded")
                    return True
                else:
                    logger.warning(f"[SECTORAL] Warning: May not be on heatmap page yet")
                    return True  # Still return True, let scraping try
            except:
                logger.warning(f"[SECTORAL] Could not verify heatmap page, proceeding anyway")
                return True
            
        except Exception as e:
            logger.error(f"[SECTORAL] Error clicking sectoral index: {e}")
            return False
    
    def _click_broad_market_index(self, index_name):
        """
        Click on a broad market index card.
        This method uses different logic optimized for broad market HTML structure.
        
        Returns:
            bool: True if successfully clicked and navigated to heatmap, False otherwise
        """
        try:
            logger.info(f"[BROAD MARKET] Clicking index: {index_name}")
            
            # Wait longer for broad market content to load after category selection
            time.sleep(5)
            
            # Scroll to top first, then down to ensure all cards are visible
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(1)
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/3);")
            time.sleep(2)
            
            # Clean up the index name for searching
            search_name = index_name.strip().upper()
            logger.info(f"[BROAD MARKET] Searching for index: '{search_name}'")
            
            clicked = False
            
            # Method 1: Use same approach as sectoral (which works) but with broad market adjustments
            try:
                # First try the same selector that works for sectoral
                all_clickables = self.driver.find_elements(By.CSS_SELECTOR, "a, div[onclick], button")
                
                logger.info(f"[BROAD MARKET] Found {len(all_clickables)} clickable elements (Method 1a)")
                
                # If that doesn't work, try broad market specific selectors
                if len(all_clickables) < 10:
                    logger.info("[BROAD MARKET] Few elements found, trying broad market specific selectors...")
                    selectors = [
                        "div[class*='index'] a",
                        "div[class*='card'] a", 
                        "a[href*='heatmap']",
                        "div[onclick*='heatmap']",
                        "div[class*='box'] a"
                    ]
                    
                    for selector in selectors:
                        try:
                            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                            all_clickables.extend(elements)
                        except:
                            continue
                    
                    # Remove duplicates
                    seen_elements = set()
                    unique_clickables = []
                    for elem in all_clickables:
                        elem_id = id(elem)
                        if elem_id not in seen_elements:
                            seen_elements.add(elem_id)
                            unique_clickables.append(elem)
                    
                    all_clickables = unique_clickables
                    logger.info(f"[BROAD MARKET] Found {len(all_clickables)} total clickable elements (Method 1b)")
                
                for card in unique_clickables:
                    try:
                        if not card.is_displayed():
                            continue
                            
                        card_text = card.text.strip()
                        if not card_text:
                            continue
                        
                        # Get first line (the index name)
                        first_line = card_text.split('\n')[0].strip().upper()
                        
                        # Check for match - exact or contains
                        is_match = (search_name == first_line or 
                                   search_name in first_line or
                                   first_line in search_name)
                        
                        if is_match:
                            logger.info(f"[BROAD MARKET] ✓ MATCH FOUND!")
                            logger.info(f"  Searching for: '{search_name}'")
                            logger.info(f"  Found card with: '{first_line}'")
                            logger.info(f"  Full text: {card_text[:100]}")
                            
                            # Try to extract JavaScript function
                            href = card.get_attribute('href')
                            onclick = card.get_attribute('onclick')
                            data_onclick = card.get_attribute('data-onclick')
                            
                            logger.info(f"  href: {href}")
                            logger.info(f"  onclick: {onclick}")
                            logger.info(f"  data-onclick: {data_onclick}")
                            logger.info(f"  tag: {card.tag_name}")
                            logger.info(f"  classes: {card.get_attribute('class')}")
                            
                            # Try multiple click strategies for broad market (same order as sectoral)
                            if href and 'javascript:' in href:
                                js_func = href.replace('javascript:', '')
                                logger.info(f"[BROAD MARKET] Executing JS from href: {js_func[:100]}...")
                                try:
                                    self.driver.execute_script(js_func)
                                    time.sleep(6)
                                    clicked = True
                                    logger.info(f"[BROAD MARKET] ✓ Clicked via href JS")
                                    break
                                except Exception as e:
                                    logger.error(f"[BROAD MARKET] Error executing href JS: {e}")
                                    continue
                            elif onclick:
                                logger.info(f"[BROAD MARKET] Executing onclick: {onclick[:100]}...")
                                try:
                                    self.driver.execute_script(onclick)
                                    time.sleep(6)
                                    clicked = True
                                    logger.info(f"[BROAD MARKET] ✓ Clicked via onclick")
                                    break
                                except Exception as e:
                                    logger.error(f"[BROAD MARKET] Error executing onclick: {e}")
                                    continue
                            elif data_onclick:
                                logger.info(f"[BROAD MARKET] Executing data-onclick: {data_onclick[:100]}...")
                                try:
                                    self.driver.execute_script(data_onclick)
                                    time.sleep(6)
                                    clicked = True
                                    logger.info(f"[BROAD MARKET] ✓ Clicked via data-onclick")
                                    break
                                except Exception as e:
                                    logger.error(f"[BROAD MARKET] Error executing data-onclick: {e}")
                                    continue
                            else:
                                # Try scrolling and clicking with multiple methods (same as sectoral)
                                logger.info(f"[BROAD MARKET] Using direct JavaScript click (no href/onclick)...")
                                
                                # Scroll element into view
                                try:
                                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", card)
                                    time.sleep(1.5)
                                    
                                    # Try click via JavaScript (same as sectoral)
                                    self.driver.execute_script("arguments[0].click();", card)
                                    time.sleep(6)
                                    clicked = True
                                    logger.info(f"[BROAD MARKET] ✓ Clicked via direct JS click")
                                    break
                                except Exception as e:
                                    logger.error(f"[BROAD MARKET] Error with direct click: {e}")
                                    # Fallback: try ActionChains if available
                                    try:
                                        from selenium.webdriver.common.action_chains import ActionChains
                                        ActionChains(self.driver).move_to_element(card).click().perform()
                                        time.sleep(6)
                                        clicked = True
                                        logger.info(f"[BROAD MARKET] ✓ Clicked via ActionChains")
                                        break
                                    except Exception as e2:
                                        logger.error(f"[BROAD MARKET] Error with ActionChains: {e2}")
                                        continue
                    
                    except Exception as e:
                        logger.debug(f"[BROAD MARKET] Error with card: {e}")
                        continue
                
            except Exception as e:
                logger.error(f"[BROAD MARKET] Method 1 failed: {e}")
            
            if not clicked:
                # Method 2: Try XPath search with broader matching
                logger.info("[BROAD MARKET] Method 1 failed, trying method 2...")
                try:
                    # Use XPath to find any element containing the index name
                    xpath = f"//*[contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{search_name}')]"
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    
                    logger.info(f"[BROAD MARKET] Found {len(elements)} elements via XPath")
                    
                    for elem in elements:
                        try:
                            if not elem.is_displayed():
                                continue
                            
                            # Find the clickable parent - try multiple ancestor patterns
                            clickable = None
                            try:
                                clickable = elem.find_element(By.XPATH, "./ancestor-or-self::*[self::a][1]")
                            except:
                                try:
                                    clickable = elem.find_element(By.XPATH, "./ancestor-or-self::*[self::div[@onclick]][1]")
                                except:
                                    try:
                                        clickable = elem.find_element(By.XPATH, "./ancestor-or-self::*[self::button][1]")
                                    except:
                                        clickable = elem
                            
                            if clickable:
                                logger.info(f"[BROAD MARKET] Found via XPath: {elem.text[:50]}")
                                
                                # Scroll into view
                                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", clickable)
                                time.sleep(1.5)
                                
                                href = clickable.get_attribute('href')
                                onclick = clickable.get_attribute('onclick')
                                
                                if href and 'javascript:' in href:
                                    js_func = href.replace('javascript:', '')
                                    self.driver.execute_script(js_func)
                                    time.sleep(6)
                                    clicked = True
                                    break
                                elif onclick:
                                    self.driver.execute_script(onclick)
                                    time.sleep(6)
                                    clicked = True
                                    break
                                else:
                                    self.driver.execute_script("arguments[0].click();", clickable)
                                    time.sleep(6)
                                    clicked = True
                                    break
                        except:
                            continue
                except Exception as e:
                    logger.error(f"[BROAD MARKET] Method 2 failed: {e}")
            
            if not clicked:
                logger.error(f"[BROAD MARKET] Could not find or click index: {index_name}")
                logger.error(f"[BROAD MARKET] Available cards on page:")
                try:
                    debug_cards = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'NIFTY')]")[:10]
                    for i, dc in enumerate(debug_cards):
                        logger.error(f"  Card {i+1}: {dc.text[:80]}")
                except:
                    pass
                return False
            
            # Verify we're on the heatmap page (not still on index list)
            time.sleep(4)
            try:
                # First, check if we're STILL on the index list page (bad sign)
                index_list_indicators = self.driver.find_elements(
                    By.XPATH,
                    "//*[contains(text(), 'Broad Market Indices')] | //*[contains(text(), 'NIFTY 50')] | //*[contains(text(), 'NIFTY NEXT 50')]"
                )
                
                # Check if we're on heatmap page by looking for heatmap-specific elements
                # Broad market heatmap pages should have stock tiles
                heatmap_indicators = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "div[class*='heatmap'], div[id*='heatmap'], [class*='tile'], [class*='stock'], [class*='grid']"
                )
                
                # Also check URL or page title
                current_url = self.driver.current_url
                page_title = self.driver.title
                
                # Count potential stock symbols (heatmap should have many)
                potential_stocks = self.driver.find_elements(
                    By.XPATH,
                    "//*[text()][string-length(text()) < 20][contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), 'NIFTY') = false]"
                )
                
                # Stricter verification: must have heatmap indicators AND not be on index list
                has_heatmap = len(heatmap_indicators) > 5
                has_stocks = len(potential_stocks) > 10
                url_has_heatmap = 'heatmap' in current_url.lower() or 'heatmap' in page_title.lower()
                still_on_index_list = len(index_list_indicators) > 3  # If we see many index names, we're still on list
                
                logger.info(f"[BROAD MARKET] Verification:")
                logger.info(f"  Heatmap indicators: {len(heatmap_indicators)}")
                logger.info(f"  Potential stocks: {len(potential_stocks)}")
                logger.info(f"  URL: {current_url}")
                logger.info(f"  Still on index list: {still_on_index_list}")
                
                if still_on_index_list and not has_heatmap:
                    logger.error(f"[BROAD MARKET] ✗ Still on index list page! Click may have failed.")
                    return False
                
                if has_heatmap or (has_stocks and url_has_heatmap):
                    logger.info(f"[BROAD MARKET] ✓ Verified: Heatmap page loaded")
                    return True
                else:
                    logger.warning(f"[BROAD MARKET] ⚠ Warning: May not be on heatmap page (found {len(heatmap_indicators)} indicators, {len(potential_stocks)} potential stocks)")
                    # Don't return True if we clearly failed
                    if len(heatmap_indicators) == 0 and len(potential_stocks) < 5:
                        logger.error(f"[BROAD MARKET] ✗ No heatmap indicators found, click likely failed")
                        return False
                    return True  # Still return True if we have some indicators
            except Exception as e:
                logger.error(f"[BROAD MARKET] Error during verification: {e}")
                return False  # Return False on error to be safe
            
        except Exception as e:
            logger.error(f"[BROAD MARKET] Error clicking broad market index: {e}")
            return False
    
    def get_heatmap(self, category_key, index_name):
        """Get heatmap data for an index"""
        try:
            with driver_lock:
                if not self.driver:
                    if not self._init_driver():
                        return None
                
                if not self._navigate_to_page():
                    return None
                
                # Select category and wait
                if not self._select_category(category_key):
                    logger.error(f"Failed to select category: {category_key}")
                    return None
                
                # Route to appropriate click method based on category
                clicked = False
                if category_key == 'broad-market':
                    clicked = self._click_broad_market_index(index_name)
                elif category_key in ['sectoral', 'thematic', 'strategy']:
                    clicked = self._click_sectoral_index(index_name)
                else:
                    logger.error(f"Unknown category: {category_key}")
                    return None
                
                if not clicked:
                    logger.error(f"Failed to click index: {index_name}")
                    return None
                
                # Wait for heatmap to load
                logger.info("Waiting for heatmap to load...")
                time.sleep(5)
                
                # Scroll the page to load all elements
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
                self.driver.execute_script("window.scrollTo(0, 0);")
                time.sleep(2)
                
                # Scrape heatmap - try multiple methods
                stocks = []
                seen_symbols = set()
                
                logger.info("Scraping heatmap tiles...")
                
                # Method 1: Try to find heatmap container first, then tiles within it
                stocks = []
                seen_symbols = set()
                
                # Look for common heatmap container classes/ids
                heatmap_containers = []
                try:
                    containers = self.driver.find_elements(By.CSS_SELECTOR, 
                        "[id*='heatmap'], [class*='heatmap'], [id*='grid'], [class*='grid'], [class*='tile'], [class*='box']")
                    heatmap_containers = [c for c in containers if c.is_displayed()]
                    logger.info(f"Found {len(heatmap_containers)} potential heatmap containers")
                except:
                    pass
                
                # Method 1a: Search within containers if found
                if heatmap_containers:
                    for container in heatmap_containers:
                        try:
                            tiles = container.find_elements(By.CSS_SELECTOR, "div, a, span")
                            for tile in tiles:
                                try:
                                    if not tile.is_displayed():
                                        continue
                                    
                                    text = tile.text.strip()
                                    if not text or len(text) < 3:
                                        continue
                                    
                                    lines = [l.strip() for l in text.split('\n') if l.strip()]
                                    
                                    if len(lines) >= 2:
                                        symbol = lines[0].strip()
                                        symbol_clean = symbol.replace(' ', '').replace('&', '').replace('-', '').replace('.', '')
                                        
                                        if (len(symbol) >= 2 and len(symbol) <= 20 and
                                            symbol_clean.isalnum() and
                                            any(c.isalpha() for c in symbol) and
                                            not symbol.replace('.', '').replace(',', '').isdigit() and
                                            symbol not in seen_symbols):
                                            
                                            # Check for price
                                            if any(c.isdigit() for c in lines[1]):
                                                seen_symbols.add(symbol)
                                                
                                                price_parts = lines[1].replace(',', '').split()
                                                price = price_parts[0] if price_parts else lines[1]
                                                change = price_parts[1] if len(price_parts) > 1 else (lines[2] if len(lines) > 2 else '')
                                                
                                                try:
                                                    bg_color = tile.value_of_css_property('background-color')
                                                    if 'rgba(0, 0, 0, 0)' in bg_color:
                                                        parent = tile.find_element(By.XPATH, "./ancestor::*[1]")
                                                        bg_color = parent.value_of_css_property('background-color')
                                                except:
                                                    bg_color = 'unknown'
                                                
                                                stock_data = {
                                                    'symbol': symbol,
                                                    'price': price,
                                                    'change': change,
                                                    'color': bg_color,
                                                    'trend': 'unknown'
                                                }
                                                
                                                stocks.append(stock_data)
                                except:
                                    continue
                        except:
                            continue
                    
                    logger.info(f"Method 1a (containers) found {len(stocks)} stocks")
                
                # Method 1b: Find all clickable/visible tiles in the heatmap grid
                # Look for elements that might be stock tiles
                potential_tiles = self.driver.find_elements(
                    By.CSS_SELECTOR,
                    "div, a, span, td"
                )
                
                logger.info(f"Found {len(potential_tiles)} potential elements for Method 1b")
                
                for tile in potential_tiles:
                    try:
                        # Skip if not visible
                        if not tile.is_displayed():
                            continue
                        
                        text = tile.text.strip()
                        
                        if not text or len(text) < 3:
                            continue
                        
                        # Skip navigation elements
                        skip_texts = ['scan', 'download', 'login', 'nse', 'ncfm', 'back', 
                                     'streaming', 'as on', 'note', 'heatmap', 'indices',
                                     'nifty', 'broad market', 'sectoral', 'thematic', 'strategy']
                        
                        if any(skip in text.lower() for skip in skip_texts):
                            continue
                        
                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        
                        # Pattern: SYMBOL \n PRICE [CHANGE]
                        # Should have at least 2 lines
                        if len(lines) >= 2:
                            symbol = lines[0].strip()
                            
                            # Validate symbol:
                            # - 2-20 chars
                            # - Mostly uppercase letters/numbers
                            # - Not a number
                            # - Not navigation text
                            
                            # More lenient validation - allow mixed case
                            symbol_clean = symbol.replace(' ', '').replace('&', '').replace('-', '').replace('.', '')
                            
                            if (len(symbol) >= 2 and len(symbol) <= 20 and
                                symbol_clean.isalnum() and
                                any(c.isalpha() for c in symbol) and
                                not symbol.replace('.', '').replace(',', '').isdigit()):
                                
                                # Check if second line has price (contains numbers)
                                price_line = lines[1]
                                if any(c.isdigit() for c in price_line):
                                    # Avoid duplicates
                                    if symbol in seen_symbols:
                                        continue
                                    
                                    seen_symbols.add(symbol)
                                    
                                    # Parse price and change
                                    price_parts = price_line.replace(',', '').split()
                                    price = price_parts[0] if price_parts else price_line
                                    
                                    # Change might be in line 2 or line 3
                                    change = ''
                                    if len(price_parts) > 1:
                                        change = price_parts[1]
                                    elif len(lines) > 2:
                                        change = lines[2]
                                    
                                    # Get the tile element (might be parent)
                                    tile_elem = tile
                                    
                                    # Try to find a parent with background color
                                    try:
                                        # Check parent elements for color
                                        for level in range(3):
                                            try:
                                                parent = tile_elem.find_element(By.XPATH, "./ancestor::*[{}]".format(level + 1))
                                                bg_color = parent.value_of_css_property('background-color')
                                                
                                                # Valid color (not transparent)
                                                if bg_color and 'rgba(0, 0, 0, 0)' not in bg_color and 'transparent' not in bg_color.lower():
                                                    break
                                            except:
                                                continue
                                        
                                        # If still no color, use tile itself
                                        if 'rgba(0, 0, 0, 0)' in bg_color or 'transparent' in bg_color.lower():
                                            bg_color = tile_elem.value_of_css_property('background-color')
                                        
                                    except:
                                        bg_color = tile_elem.value_of_css_property('background-color')
                                    
                                    stock_data = {
                                        'symbol': symbol,
                                        'price': price,
                                        'change': change,
                                        'color': bg_color if bg_color else 'unknown'
                                    }
                                    
                                    # Determine trend from color
                                    try:
                                        if 'rgb' in bg_color:
                                            rgb_parts = bg_color.replace('rgba', '').replace('rgb', '').replace('(', '').replace(')', '').split(',')
                                            if len(rgb_parts) >= 3:
                                                r = int(rgb_parts[0].strip())
                                                g = int(rgb_parts[1].strip())
                                                
                                                if g > r + 20:
                                                    stock_data['trend'] = 'gain'
                                                elif r > g + 20:
                                                    stock_data['trend'] = 'loss'
                                                else:
                                                    stock_data['trend'] = 'neutral'
                                            else:
                                                stock_data['trend'] = 'unknown'
                                        else:
                                            stock_data['trend'] = 'unknown'
                                    except:
                                        stock_data['trend'] = 'unknown'
                                    
                                    stocks.append(stock_data)
                                    logger.debug(f"Found stock: {symbol} - {price} ({change})")
                    
                    except Exception as e:
                        logger.debug(f"Error processing tile: {e}")
                        continue
                
                logger.info(f"Found {len(stocks)} stocks via Method 1")
                
                # Method 2: If we got very few stocks, try a different approach
                if len(stocks) < 3:
                    logger.info("Method 1 found few stocks, trying Method 2...")
                    
                    # Look for all text elements and find those with stock-like patterns
                    all_text_elements = self.driver.find_elements(By.XPATH, "//*[text()]")
                    
                    for elem in all_text_elements:
                        try:
                            if not elem.is_displayed():
                                continue
                            
                            text = elem.text.strip()
                            if not text or len(text) < 3:
                                continue
                            
                            lines = [l.strip() for l in text.split('\n') if l.strip()]
                            
                            if len(lines) >= 2:
                                symbol = lines[0].strip()
                                
                                # More lenient validation
                                if (len(symbol) >= 2 and len(symbol) <= 25 and
                                    any(c.isalpha() for c in symbol) and
                                    symbol not in seen_symbols and
                                    not any(skip in symbol.lower() for skip in skip_texts)):
                                    
                                    # Check for price pattern
                                    if any(c.isdigit() for c in lines[1]):
                                        seen_symbols.add(symbol)
                                        
                                        price_parts = lines[1].replace(',', '').split()
                                        price = price_parts[0] if price_parts else lines[1]
                                        change = price_parts[1] if len(price_parts) > 1 else (lines[2] if len(lines) > 2 else '')
                                        
                                        # Get color from element or parent
                                        try:
                                            bg_color = elem.value_of_css_property('background-color')
                                            if 'rgba(0, 0, 0, 0)' in bg_color:
                                                parent = elem.find_element(By.XPATH, "./ancestor::*[1]")
                                                bg_color = parent.value_of_css_property('background-color')
                                        except:
                                            bg_color = 'unknown'
                                        
                                        stock_data = {
                                            'symbol': symbol,
                                            'price': price,
                                            'change': change,
                                            'color': bg_color,
                                            'trend': 'unknown'
                                        }
                                        
                                        stocks.append(stock_data)
                                        logger.debug(f"Found stock (Method 2): {symbol}")
                        except:
                            continue
                    
                    logger.info(f"Method 2 added, total stocks: {len(stocks)}")
                
                # Final duplicate removal (safety check)
                seen = set()
                unique_stocks = []
                for stock in stocks:
                    if stock['symbol'] not in seen:
                        seen.add(stock['symbol'])
                        unique_stocks.append(stock)
                
                logger.info(f"Final count: {len(unique_stocks)} unique stocks scraped")
                
                # Log first few stocks for debugging
                if unique_stocks:
                    logger.info(f"Sample stocks: {[s['symbol'] for s in unique_stocks[:5]]}")
                else:
                    logger.warning("No stocks found! Page might have different structure.")
                    # Try to get page source snippet for debugging
                    try:
                        page_text = self.driver.find_element(By.TAG_NAME, "body").text[:500]
                        logger.debug(f"Page text sample: {page_text}")
                    except:
                        pass
                
                return {
                    'index_name': index_name,
                    'category': self.categories[category_key],
                    'total_stocks': len(unique_stocks),
                    'scrape_timestamp': datetime.now().isoformat(),
                    'stocks': unique_stocks
                }
                
        except Exception as e:
            logger.error(f"Error getting heatmap: {e}")
            return None
    
    def cleanup(self):
        """Close driver"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


# Global service instance
heatmap_service = HeatmapService()


@app.route('/')
def index():
    """API documentation"""
    return jsonify({
        'name': 'NSE Heatmap API',
        'version': '1.0',
        'description': 'Real-time NSE market heatmap data',
        'endpoints': {
            'GET /': 'API documentation',
            'GET /health': 'Health check',
            'GET /categories': 'List all categories',
            'GET /indices?category=broad-market': 'List indices for a category',
            'GET /heatmap?category=broad-market&index=NIFTY 50': 'Get heatmap data'
        },
        'parameters': {
            'category': 'Category key (broad-market, sectoral, thematic, strategy)',
            'index': 'Index name (e.g., NIFTY 50, NIFTY BANK)'
        },
        'examples': [
            '/categories',
            '/indices?category=broad-market',
            '/indices?category=sectoral',
            '/heatmap?category=broad-market&index=NIFTY 50',
            '/heatmap?category=sectoral&index=NIFTY BANK'
        ]
    })


@app.route('/health')
def health():
    """Health check"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'heatmap-api'
    })


@app.route('/categories')
def get_categories():
    """Get all available categories"""
    categories = [
        {
            'key': 'broad-market',
            'name': 'Broad Market Indices',
            'description': 'Major market indices like NIFTY 50, NIFTY NEXT 50'
        },
        {
            'key': 'sectoral',
            'name': 'Sectoral Indices',
            'description': 'Sector-specific indices like NIFTY BANK, NIFTY IT'
        },
        {
            'key': 'thematic',
            'name': 'Thematic Indices',
            'description': 'Theme-based indices'
        },
        {
            'key': 'strategy',
            'name': 'Strategy Indices',
            'description': 'Strategy-based indices'
        }
    ]
    
    return jsonify({
        'success': True,
        'total': len(categories),
        'categories': categories
    })


@app.route('/indices')
def get_indices():
    """Get indices for a category"""
    category = request.args.get('category', 'broad-market')
    
    if category not in heatmap_service.categories:
        return jsonify({
            'success': False,
            'error': f'Invalid category. Use: {", ".join(heatmap_service.categories.keys())}'
        }), 400
    
    logger.info(f"Fetching indices for category: {category}")
    
    indices = heatmap_service.get_indices(category)
    
    if indices is None:
        return jsonify({
            'success': False,
            'error': 'Failed to fetch indices. Please try again.'
        }), 500
    
    return jsonify({
        'success': True,
        'category': category,
        'category_name': heatmap_service.categories[category],
        'total': len(indices),
        'indices': indices,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/heatmap')
def get_heatmap():
    """Get heatmap data for an index"""
    category = request.args.get('category', 'broad-market')
    index_name = request.args.get('index')
    
    if not index_name:
        return jsonify({
            'success': False,
            'error': 'Missing required parameter: index'
        }), 400
    
    if category not in heatmap_service.categories:
        return jsonify({
            'success': False,
            'error': f'Invalid category. Use: {", ".join(heatmap_service.categories.keys())}'
        }), 400
    
    logger.info(f"Fetching heatmap for: {index_name} in {category}")
    
    heatmap_data = heatmap_service.get_heatmap(category, index_name)
    
    if heatmap_data is None:
        return jsonify({
            'success': False,
            'error': f'Failed to fetch heatmap for {index_name}. Index may not exist.'
        }), 500
    
    return jsonify({
        'success': True,
        'data': heatmap_data
    })


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found. Visit / for documentation.'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


if __name__ == '__main__':
    import os
    
    port = int(os.environ.get('PORT', 5001))
    
    print("\n" + "=" * 80)
    print("NSE HEATMAP API")
    print("=" * 80)
    print(f"\nAPI Server: http://localhost:{port}")
    print("\nEndpoints:")
    print(f"  GET  /                              - API Documentation")
    print(f"  GET  /health                        - Health Check")
    print(f"  GET  /categories                    - List All Categories")
    print(f"  GET  /indices?category=broad-market - List Indices")
    print(f"  GET  /heatmap?category=broad-market&index=NIFTY 50 - Get Heatmap")
    print("\nExamples:")
    print(f"  curl http://localhost:{port}/categories")
    print(f"  curl http://localhost:{port}/indices?category=sectoral")
    print(f"  curl 'http://localhost:{port}/heatmap?category=broad-market&index=NIFTY 50'")
    print("\n" + "=" * 80)
    print("Press Ctrl+C to stop\n")
    
    try:
        app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
    finally:
        heatmap_service.cleanup()

