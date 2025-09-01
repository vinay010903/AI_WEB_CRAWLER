#!/usr/bin/env python3
"""
Test script for SelectorCategorizer with different AI providers

This script tests the SelectorCategorizer with both Groq and local LM providers.
"""

import json
from selector_categorizer import SelectorCategorizer

# Sample selector data for testing
sample_selectors = {
    "id_selectors": [
        {
            "uuid": "4d4634de-92e1-4bf4-ab37-f03448648a8d",
            "selector": "#nav-tools",
            "tag": "div",
            "text_content": "ENHello, sign inAccount & ListsReturns& Orders0Cart"
        },
        {
            "uuid": "ccb1e695-0de9-42e5-9bc6-b51a1761661d",
            "selector": "#icp-nav-flyout",
            "tag": "div",
            "text_content": "EN"
        },
        {
            "uuid": "77d5eca2-01e9-4187-9de7-2a95eeb8588c",
            "selector": "#nav-link-accountList",
            "tag": "div",
            "text_content": "Hello, sign inAccount & Lists"
        }
    ],
    "class_selectors": [
        {
            "uuid": "f94e53b7-df3a-44a1-831e-e91f203c1b1c",
            "selector": ".search-bar",
            "tag": "input",
            "text_content": "Search products..."
        },
        {
            "uuid": "fdef0d0c-d3c9-49f6-b1ec-b6104d27ff09",
            "selector": ".product-price",
            "tag": "span",
            "text_content": "$29.99"
        }
    ],
    "statistics": {
        "url": "https://example.com",
        "total_elements": 5
    }
}

def test_groq_provider():
    """Test SelectorCategorizer with Groq provider."""
    print("=" * 60)
    print("Testing Groq Provider")
    print("=" * 60)
    
    try:
        categorizer = SelectorCategorizer(provider="local")
        print(f"✅ Groq categorizer initialized: {categorizer}")
        
        # Test categorization
        result = categorizer.categorize_selectors_with_ai(sample_selectors)
        
        if result:
            print("✅ Groq categorization completed successfully!")
            print(f"Total items: {len(result)}")
            
            # Print first few results
            for item in result[:5]:  # Show first 5 items
                print(f"  - {item.get('category', 'N/A')}: {item.get('uuid', 'N/A')} (confidence: {item.get('confidence', 'N/A')})")
        else:
            print("❌ Groq categorization returned empty result")
            
    except Exception as e:
        print(f"❌ Groq provider test failed: {e}")

def test_local_provider():
    """Test SelectorCategorizer with local LM provider."""
    print("\n" + "=" * 60)
    print("Testing Local LM Provider")
    print("=" * 60)
    
    try:
        categorizer = SelectorCategorizer(
            provider="local",
            local_model_url="http://localhost:1234",
            local_model_name="openai/gpt-oss-20b",
            timeout=120.0
        )
        print(f"✅ Local LM categorizer initialized: {categorizer}")
        
        # Test categorization
        result = categorizer.categorize_selectors_with_ai(sample_selectors)

        print(f"📝 Result  ===> : {result} )")
        
        if result:
            print("✅ Local LM categorization completed successfully!")
            print(f"Total items: {len(result)}")
            
            # Print first few results
            for item in result[:5]:  # Show first 5 items
                print(f"  - {item.get('category', 'N/A')}: {item.get('uuid', 'N/A')} (confidence: {item.get('confidence', 'N/A')})")
        else:
            print("❌ Local LM categorization returned empty result")
            
    except Exception as e:
        print(f"❌ Local LM provider test failed: {e}")


def main():
    """Main test function."""
    print("🧪 Testing SelectorCategorizer with Different AI Providers")
    print("=" * 80)
    
    # Test individual providers
    # test_groq_provider()
    test_local_provider()

    
    print("\n" + "=" * 80)
    print("🎉 Provider tests completed!")

if __name__ == "__main__":
    main()