#!/usr/bin/env python3
"""
Test script to extract all selectors from a website URL using BeautifulSoup.
This script fetches a webpage and extracts various types of CSS selectors.
"""

import requests
from bs4 import BeautifulSoup
import json
import sys
from urllib.parse import urljoin, urlparse
import time
import uuid
from typing import List, Dict, Set
import os


def fetch_website_content(url: str) -> str:
    """
    Fetch the HTML content from a website URL.
    
    Args:
        url (str): The website URL to fetch
        
    Returns:
        str: HTML content of the website
        
    Raises:
        requests.RequestException: If there's an error fetching the content
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        print(f"🌐 Fetching content from: {url}")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        print(f"✅ Successfully fetched {len(response.content)} bytes")
        return response.text
        
    except requests.RequestException as e:
        print(f"❌ Error fetching content from {url}: {e}")
        raise


def extract_all_selectors(html_content: str, url: str = None) -> Dict:
    """
    Extract all possible CSS selectors from HTML content using BeautifulSoup.
    
    Args:
        html_content (str): HTML content to parse
        url (str): Original URL (for context)
        
    Returns:
        Dict: Dictionary containing different types of selectors
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    selectors = {
        'id_selectors': [],
        'class_selectors': [],
        'name_selectors': [],
        'type_selectors': [],
        'attribute_selectors': [],
        'input_selectors': [],
        'button_selectors': [],
        'link_selectors': [],
        'form_selectors': [],
        'combined_selectors': [],
        'statistics': {
            'total_elements': 0,
            'elements_with_id': 0,
            'elements_with_class': 0,
            'elements_with_name': 0,
            'unique_tags': set(),
            'url': url
        }
    }
    
    print("🔍 Extracting selectors from HTML content...")
    
    # Find all elements
    all_elements = soup.find_all()
    selectors['statistics']['total_elements'] = len(all_elements)
    
    # Track unique selectors to avoid duplicates
    unique_ids = set()
    unique_classes = set()
    unique_names = set()
    unique_attributes = set()
    
    for element in all_elements:
        tag_name = element.name
        selectors['statistics']['unique_tags'].add(tag_name)
        
        # Extract ID selectors
        if element.get('id'):
            element_id = element.get('id')
            if element_id not in unique_ids:
                unique_ids.add(element_id)
                selectors['id_selectors'].append({
                    'uuid': str(uuid.uuid4()),
                    'selector': f"#{element_id}",
                    'tag': tag_name,
                    'text_content': element.get_text(strip=True)[:200] if element.get_text(strip=True) else ''
                })
                selectors['statistics']['elements_with_id'] += 1
        
        # Extract class selectors
        if element.get('class'):
            classes = element.get('class')
            for class_name in classes:
                if class_name not in unique_classes:
                    unique_classes.add(class_name)
                    selectors['class_selectors'].append({
                        'uuid': str(uuid.uuid4()),
                        'selector': f".{class_name}",
                        'tag': tag_name,
                        'text_content': element.get_text(strip=True)[:200] if element.get_text(strip=True) else ''
                    })
            selectors['statistics']['elements_with_class'] += 1
        
        # Extract name selectors (for form elements)
        if element.get('name'):
            name = element.get('name')
            if name not in unique_names:
                unique_names.add(name)
                selectors['name_selectors'].append({
                    'uuid': str(uuid.uuid4()),
                    'selector': f"[name='{name}']",
                    'tag': tag_name,
                    'type': element.get('type', ''),
                    'text_content': element.get_text(strip=True)[:200] if element.get_text(strip=True) else ''
                })
                selectors['statistics']['elements_with_name'] += 1
        
        # Extract type selectors for form elements
        if tag_name in ['input', 'button', 'select', 'textarea'] and element.get('type'):
            element_type = element.get('type')
            type_selector = f"input[type='{element_type}']" if tag_name == 'input' else f"{tag_name}[type='{element_type}']"
            selectors['type_selectors'].append({
                'uuid': str(uuid.uuid4()),
                'selector': type_selector,
                'tag': tag_name,
                'name': element.get('name', ''),
                'id': element.get('id', ''),
                'text_content': element.get_text(strip=True)[:200] if element.get_text(strip=True) else ''
            })
        
        # Extract other important attributes
        important_attrs = ['data-testid', 'data-hook', 'data-component-type', 'role', 'aria-label', 'placeholder']
        for attr in important_attrs:
            if element.get(attr):
                attr_value = element.get(attr)
                attr_selector = f"[{attr}='{attr_value}']"
                if attr_selector not in unique_attributes:
                    unique_attributes.add(attr_selector)
                    selectors['attribute_selectors'].append({
                        'uuid': str(uuid.uuid4()),
                        'selector': attr_selector,
                        'tag': tag_name,
                        'attribute': attr,
                        'value': attr_value,
                        'text_content': element.get_text(strip=True)[:200] if element.get_text(strip=True) else ''
                    })
        
        # Special handling for input elements
        if tag_name == 'input':
            input_data = {
                'uuid': str(uuid.uuid4()),
                'tag': tag_name,
                'type': element.get('type', 'text'),
                'name': element.get('name', ''),
                'id': element.get('id', ''),
                'placeholder': element.get('placeholder', ''),
                'selectors': []
            }
            
            # Generate multiple selector options for inputs
            if element.get('id'):
                input_data['selectors'].append(f"#{element.get('id')}")
            if element.get('name'):
                input_data['selectors'].append(f"input[name='{element.get('name')}']")
            if element.get('type'):
                input_data['selectors'].append(f"input[type='{element.get('type')}']")
            if element.get('placeholder'):
                input_data['selectors'].append(f"input[placeholder='{element.get('placeholder')}']")
            
            selectors['input_selectors'].append(input_data)
        
        # Special handling for button elements
        if tag_name in ['button', 'input'] and element.get('type') in ['button', 'submit', 'reset']:
            button_text = element.get_text(strip=True) or element.get('value', '')
            button_data = {
                'uuid': str(uuid.uuid4()),
                'tag': tag_name,
                'type': element.get('type', 'button'),
                'text': button_text[:50],
                'id': element.get('id', ''),
                'name': element.get('name', ''),
                'selectors': []
            }
            
            if element.get('id'):
                button_data['selectors'].append(f"#{element.get('id')}")
            if element.get('name'):
                button_data['selectors'].append(f"{tag_name}[name='{element.get('name')}']")
            if element.get('type'):
                button_data['selectors'].append(f"{tag_name}[type='{element.get('type')}']")
            
            selectors['button_selectors'].append(button_data)
        
        # Special handling for links
        if tag_name == 'a' and element.get('href'):
            href = element.get('href')
            link_text = element.get_text(strip=True)
            selectors['link_selectors'].append({
                'uuid': str(uuid.uuid4()),
                'selector': f"a[href='{href}']" if len(href) < 100 else "a",
                'href': href,
                'text': link_text[:100],
                'id': element.get('id', ''),
                'class': ' '.join(element.get('class', []))
            })
        
        # Special handling for forms
        if tag_name == 'form':
            form_data = {
                'uuid': str(uuid.uuid4()),
                'tag': tag_name,
                'action': element.get('action', ''),
                'method': element.get('method', 'get'),
                'id': element.get('id', ''),
                'name': element.get('name', ''),
                'selectors': []
            }
            
            if element.get('id'):
                form_data['selectors'].append(f"#{element.get('id')}")
            if element.get('name'):
                form_data['selectors'].append(f"form[name='{element.get('name')}']")
            if element.get('action'):
                form_data['selectors'].append(f"form[action='{element.get('action')}']")
            
            selectors['form_selectors'].append(form_data)
    
    # Generate some useful combined selectors
    selectors['combined_selectors'] = generate_combined_selectors(soup)
    
    # Convert set to list for JSON serialization
    selectors['statistics']['unique_tags'] = list(selectors['statistics']['unique_tags'])
    
    print(f"✅ Extracted {len(selectors['id_selectors'])} ID selectors")
    print(f"✅ Extracted {len(selectors['class_selectors'])} class selectors")
    print(f"✅ Extracted {len(selectors['name_selectors'])} name selectors")
    print(f"✅ Extracted {len(selectors['input_selectors'])} input selectors")
    print(f"✅ Extracted {len(selectors['button_selectors'])} button selectors")
    print(f"✅ Extracted {len(selectors['link_selectors'])} link selectors")
    print(f"✅ Found {len(selectors['statistics']['unique_tags'])} unique HTML tags")
    
    return selectors


def generate_combined_selectors(soup: BeautifulSoup) -> List[Dict]:
    """
    Generate useful combined selectors for common patterns.
    
    Args:
        soup (BeautifulSoup): Parsed HTML soup
        
    Returns:
        List[Dict]: List of combined selector patterns
    """
    combined = []
    
    # Login-related selectors
    login_patterns = [
        "input[type='email']",
        "input[type='password']",
        "input[name*='email']",
        "input[name*='username']",
        "input[name*='login']",
        "input[name*='password']",
        "button[type='submit']",
        "input[type='submit']",
        "[class*='login']",
        "[class*='signin']",
        "[id*='login']",
        "[id*='signin']"
    ]
    
    for pattern in login_patterns:
        elements = soup.select(pattern)
        if elements:
            combined.append({
                'pattern': pattern,
                'description': 'Login/Authentication related',
                'count': len(elements),
                'sample_elements': [
                    {
                        'tag': elem.name,
                        'attributes': dict(elem.attrs),
                        'text': elem.get_text(strip=True)[:50]
                    } for elem in elements[:3]  # Show first 3 matches
                ]
            })
    
    # Search-related selectors
    search_patterns = [
        "input[type='search']",
        "input[name*='search']",
        "input[name*='query']",
        "input[name*='q']",
        "[class*='search']",
        "[id*='search']",
        "button[class*='search']",
        "input[class*='search']"
    ]
    
    for pattern in search_patterns:
        elements = soup.select(pattern)
        if elements:
            combined.append({
                'pattern': pattern,
                'description': 'Search related',
                'count': len(elements),
                'sample_elements': [
                    {
                        'tag': elem.name,
                        'attributes': dict(elem.attrs),
                        'text': elem.get_text(strip=True)[:50]
                    } for elem in elements[:3]
                ]
            })
    
    # Navigation-related selectors
    nav_patterns = [
        "nav",
        "[role='navigation']",
        ".navbar",
        ".nav",
        ".menu",
        "[class*='nav']"
    ]
    
    for pattern in nav_patterns:
        elements = soup.select(pattern)
        if elements:
            combined.append({
                'pattern': pattern,
                'description': 'Navigation related',
                'count': len(elements),
                'sample_elements': [
                    {
                        'tag': elem.name,
                        'attributes': dict(elem.attrs),
                        'text': elem.get_text(strip=True)[:50]
                    } for elem in elements[:3]
                ]
            })
    
    return combined


def save_selectors_to_file(selectors: Dict, filename: str = None):
    """
    Save extracted selectors to a JSON file.
    
    Args:
        selectors (Dict): Dictionary of extracted selectors
        filename (str): Output filename (optional)
    """
    if not filename:
        # Generate filename based on URL or timestamp
        url = selectors['statistics'].get('url', '')
        if url:
            domain = urlparse(url).netloc.replace('.', '_')
            filename = f"selectors_{domain}_{int(time.time())}.json"
        else:
            filename = f"selectors_{int(time.time())}.json"
    
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Write the selectors to the file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(selectors, f, indent=4, ensure_ascii=False)
        print(f"💾 Selectors saved to: {filename}")
    except Exception as e:
        print(f"❌ Error saving selectors to file: {e}")


def print_selector_summary(selectors: Dict):
    """
    Print a summary of extracted selectors.
    
    Args:
        selectors (Dict): Dictionary of extracted selectors
    """
    stats = selectors['statistics']
    
    print("\n" + "="*60)
    print("📊 SELECTOR EXTRACTION SUMMARY")
    print("="*60)
    print(f"URL: {stats.get('url', 'N/A')}")
    print(f"Total Elements: {stats['total_elements']}")
    print(f"Elements with ID: {stats['elements_with_id']}")
    print(f"Elements with Class: {stats['elements_with_class']}")
    print(f"Elements with Name: {stats['elements_with_name']}")
    print(f"Unique Tags: {len(stats['unique_tags'])}")
    print(f"Tags Found: {', '.join(sorted(stats['unique_tags']))}")
    
    print(f"\n📋 SELECTOR COUNTS:")
    print(f"- ID Selectors: {len(selectors['id_selectors'])}")
    print(f"- Class Selectors: {len(selectors['class_selectors'])}")
    print(f"- Name Selectors: {len(selectors['name_selectors'])}")
    print(f"- Type Selectors: {len(selectors['type_selectors'])}")
    print(f"- Attribute Selectors: {len(selectors['attribute_selectors'])}")
    print(f"- Input Selectors: {len(selectors['input_selectors'])}")
    print(f"- Button Selectors: {len(selectors['button_selectors'])}")
    print(f"- Link Selectors: {len(selectors['link_selectors'])}")
    print(f"- Form Selectors: {len(selectors['form_selectors'])}")
    print(f"- Combined Patterns: {len(selectors['combined_selectors'])}")
    
    # Show some sample selectors
    if selectors['id_selectors']:
        print(f"\n🔖 SAMPLE ID SELECTORS:")
        for selector in selectors['id_selectors'][:5]:
            print(f"  {selector['selector']} ({selector['tag']})")
    
    if selectors['class_selectors']:
        print(f"\n🎨 SAMPLE CLASS SELECTORS:")
        for selector in selectors['class_selectors'][:5]:
            print(f"  {selector['selector']} ({selector['tag']})")
    
    if selectors['input_selectors']:
        print(f"\n📝 SAMPLE INPUT SELECTORS:")
        for selector in selectors['input_selectors'][:3]:
            print(f"  Type: {selector['type']}, Selectors: {selector['selectors']}")
    
    print("="*60)


def main():
    """
    Main function to run the selector extraction.
    """
    if len(sys.argv) != 2:
        print("Usage: python test_extract_selector.py <URL>")
        print("Example: python test_extract_selector.py https://www.amazon.com")
        sys.exit(1)
    
    url = sys.argv[1]
    
    # Validate URL
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        print("❌ Invalid URL. Please provide a complete URL with http:// or https://")
        sys.exit(1)
    
    try:
        # Fetch website content
        html_content = fetch_website_content(url)
        
        # Extract selectors
        selectors = extract_all_selectors(html_content, url)
        
        # Print summary
        print_selector_summary(selectors)
        
        # Save to file
        selector_file_path = "exracted_data/selector/amazon_selectors.json"
        save_selectors_to_file(selectors,selector_file_path)
        
        print(f"\n🎉 Selector extraction completed successfully!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()