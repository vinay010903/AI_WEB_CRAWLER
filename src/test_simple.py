#!/usr/bin/env python3
"""
Simple test to demonstrate the selector extraction functionality.
"""

from test_extract_selector import extract_all_selectors, print_selector_summary
import json

# Sample HTML content for testing
sample_html = """
<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <div id="header" class="main-header">
        <h1>Welcome to Test Page</h1>
        <nav class="navbar">
            <a href="#home" class="nav-link">Home</a>
            <a href="#about" class="nav-link">About</a>
        </nav>
    </div>
    
    <main id="content" class="main-content">
        <form id="login-form" action="/login" method="post">
            <div class="form-group">
                <label for="username">Username:</label>
                <input type="text" id="username" name="username" placeholder="Enter username" required>
            </div>
            <div class="form-group">
                <label for="password">Password:</label>
                <input type="password" id="password" name="password" placeholder="Enter password" required>
            </div>
            <div class="form-group">
                <button type="submit" id="login-btn" class="btn-primary">Login</button>
                <button type="reset" class="btn-secondary">Reset</button>
            </div>
        </form>
        
        <div class="search-container" data-testid="search-widget">
            <input type="search" name="query" placeholder="Search..." class="search-input">
            <button type="button" class="search-btn" data-hook="search-button">Search</button>
        </div>
        
        <div class="product-list">
            <div class="product-item" data-component-type="product">
                <h3>Product 1</h3>
                <a href="/product/1" class="product-link">View Details</a>
            </div>
            <div class="product-item" data-component-type="product">
                <h3>Product 2</h3>
                <a href="/product/2" class="product-link">View Details</a>
            </div>
        </div>
    </main>
    
    <footer id="footer" class="site-footer">
        <p>&copy; 2024 Test Site</p>
    </footer>
</body>
</html>
"""

def main():
    print("🧪 Testing Selector Extraction with Sample HTML")
    print("=" * 50)
    
    # Extract selectors from sample HTML
    selectors = extract_all_selectors(sample_html, "http://test.example.com")
    
    # Print summary
    print_selector_summary(selectors)
    
    # Save to file
    with open("sample_selectors.json", "w", encoding="utf-8") as f:
        json.dump(selectors, f, indent=4, ensure_ascii=False)
    
    print(f"\n💾 Sample selectors saved to: sample_selectors.json")
    
    # Show some specific examples
    print(f"\n🔍 DETAILED EXAMPLES:")
    print(f"\n📝 Input Elements Found:")
    for input_elem in selectors['input_selectors']:
        print(f"  - Type: {input_elem['type']}, Name: {input_elem['name']}")
        print(f"    Selectors: {input_elem['selectors']}")
    
    print(f"\n🔘 Button Elements Found:")
    for button in selectors['button_selectors']:
        print(f"  - Text: '{button['text']}', Type: {button['type']}")
        print(f"    Selectors: {button['selectors']}")
    
    print(f"\n🔗 Links Found:")
    for link in selectors['link_selectors'][:3]:  # Show first 3
        print(f"  - Text: '{link['text']}', Href: {link['href']}")
        print(f"    Selector: {link['selector']}")
    
    print(f"\n🎯 Combined Patterns Found:")
    for pattern in selectors['combined_selectors']:
        print(f"  - Pattern: {pattern['pattern']}")
        print(f"    Description: {pattern['description']}")
        print(f"    Matches: {pattern['count']}")

if __name__ == "__main__":
    main()