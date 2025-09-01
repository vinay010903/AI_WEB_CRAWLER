import json
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
from urllib.parse import urlparse, urljoin


def extract_candidates(html_content, base_url=None, stage=None):
    """
    Enhanced candidate extraction with better filtering and context awareness.
    Args:
        html_content (str): The HTML content of the page.
        base_url (str): Base URL for resolving relative links
        stage (str): Current stage for context-aware extraction
        
    Returns:
        list: A list of dictionaries representing element candidates.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    # Stage-specific tag priorities
    if stage == "login":
        tags_to_extract = ['a', 'button', 'input', 'form', 'div', 'span', 'nav']
        priority_attrs = ['href', 'onclick', 'class', 'id', 'role', 'aria-label']
    elif stage == "auth":
        tags_to_extract = ['input', 'button', 'form', 'a', 'div', 'span']
        priority_attrs = ['type', 'name', 'id', 'placeholder', 'aria-label', 'autocomplete']
    elif stage == "product":
        tags_to_extract = ['div', 'span', 'h1', 'h2', 'h3', 'p', 'a', 'meta', 'script']
        priority_attrs = ['class', 'id', 'itemprop', 'data-testid', 'data-automation-id']
    else:
        tags_to_extract = ['input', 'button', 'a', 'form', 'div', 'span', 'h1', 'h2', 'h3']
        priority_attrs = ['class', 'id', 'name', 'type', 'href']
    
    candidates = []
    seen_elements = set()  # Avoid duplicates

    for tag in tags_to_extract:
        elements = soup.find_all(tag)
        
        for element in elements:
            try:
                # Get text content
                text_content = element.get_text(strip=True)
                
                # Skip elements with no meaningful content
                if not text_content and not element.attrs:
                    continue
                
                # Skip script tags with no relevant content
                if tag == 'script' and element.get('type') != 'application/ld+json':
                    continue
                
                # Create element signature to avoid duplicates
                element_signature = (
                    element.name,
                    str(sorted(element.attrs.items())),
                    text_content[:50]
                )
                
                if element_signature in seen_elements:
                    continue
                seen_elements.add(element_signature)
                
                # Process attributes
                processed_attrs = {}
                for attr, value in element.attrs.items():
                    if isinstance(value, list):
                        processed_attrs[attr] = value
                    else:
                        processed_attrs[attr] = str(value)
                
                # Resolve relative URLs
                if base_url and 'href' in processed_attrs:
                    try:
                        processed_attrs['href'] = urljoin(base_url, processed_attrs['href'])
                    except:
                        pass
                
                # Create candidate with enhanced information
                candidate = {
                    "tag": element.name,
                    "attrs": processed_attrs,
                    "text": text_content[:200],  # Increased limit for better context
                    "text_length": len(text_content),
                    "has_children": len(element.find_all()) > 0,
                    "parent_tag": element.parent.name if element.parent else None
                }
                
                # Add context-specific information
                if stage == "login":
                    candidate["likely_login"] = any(
                        keyword in text_content.lower() 
                        for keyword in ['sign in', 'log in', 'login', 'account']
                    ) or any(
                        keyword in str(processed_attrs).lower()
                        for keyword in ['login', 'signin', 'sign-in', 'auth']
                    )
                
                elif stage == "auth":
                    input_type = processed_attrs.get('type', '').lower()
                    candidate["input_type"] = input_type
                    candidate["likely_username"] = (
                        input_type in ['email', 'text'] or
                        any(keyword in str(processed_attrs).lower() 
                            for keyword in ['user', 'email', 'login'])
                    )
                    candidate["likely_password"] = input_type == 'password'
                    candidate["likely_submit"] = (
                        input_type == 'submit' or 
                        (element.name == 'button' and 
                         any(keyword in text_content.lower() 
                             for keyword in ['sign in', 'log in', 'login', 'submit']))
                    )
                
                elif stage == "product":
                    candidate["has_product_data"] = any(
                        keyword in str(processed_attrs).lower()
                        for keyword in ['product', 'item', 'sku', 'asin', 'rating', 'review']
                    )
                    candidate["schema_property"] = processed_attrs.get('itemprop')
                
                candidates.append(candidate)
                
            except:
                continue
    
    # Sort candidates by relevance (stage-specific)
    if stage == "login":
        candidates.sort(key=lambda x: (
            x.get("likely_login", False),
            len(x.get("text", "")),
            bool(x.get("attrs", {}).get("href"))
        ), reverse=True)
    elif stage == "auth":
        candidates.sort(key=lambda x: (
            x.get("likely_username", False) or x.get("likely_password", False) or x.get("likely_submit", False),
            x.get("tag") == "input",
            len(x.get("text", ""))
        ), reverse=True)
    elif stage == "product":
        candidates.sort(key=lambda x: (
            x.get("has_product_data", False),
            bool(x.get("schema_property")),
            len(x.get("text", ""))
        ), reverse=True)
    
    return candidates


def wait_for_page_stability(page, timeout=10000, check_interval=1000):
    """Wait for page to be stable (no ongoing network requests or DOM changes)"""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
        
        stable_count = 0
        last_content_length = 0
        
        for _ in range(5):  # Check stability 5 times
            time.sleep(check_interval / 1000)
            current_content_length = len(page.content())
            
            if current_content_length == last_content_length:
                stable_count += 1
            else:
                stable_count = 0
                last_content_length = current_content_length
            
            if stable_count >= 3:
                break
        
        return True
        
    except:
        return False


def run_convert(url: str, outfile: str, stage=None):
    """
    Enhanced convert function with better error handling and browser setup.
    """
    browser = None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,
                slow_mo=50,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-web-security',
                    '--no-sandbox'
                ]
            )
            
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.new_page()
            page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            wait_for_page_stability(page)
            
            html_content = page.content()
            candidates = extract_candidates(html_content, base_url=url, stage=stage)
            
            output_data = {
                "url": url,
                "timestamp": time.time(),
                "stage": stage,
                "total_candidates": len(candidates),
                "candidates": candidates
            }
            
            with open(outfile, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
    except Exception as e:
        raise
        
    finally:
        if browser:
            browser.close()
    
    return outfile


def run_convert_on_page(page, url: str, outfile: str, stage=None):
    """
    Enhanced version that reuses an existing Playwright page.
    """
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        
        wait_for_page_stability(page)
        
        html_content = page.content()
        candidates = extract_candidates(html_content, base_url=url, stage=stage)
        
        output_data = {
            "url": url,
            "timestamp": time.time(),
            "stage": stage,
            "total_candidates": len(candidates),
            "candidates": candidates
        }
        
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        return outfile
        
    except Exception as e:
        raise