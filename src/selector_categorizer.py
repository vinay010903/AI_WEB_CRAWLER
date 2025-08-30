#!/usr/bin/env python3
"""
Selector Categorization System using Groq AI

This script categorizes extracted selectors into predefined categories:
1. Navigation & Layout
2. Authentication & User Account  
3. Search & Filters
4. Category & Product Listing Pages
5. Product Details
6. Support & Miscellaneous
"""

import os
import json
import time
from typing import Dict, List, Optional
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class SelectorCategorizer:
    """
    Categorizes extracted selectors using Groq AI into predefined categories.
    """
    
    CATEGORIES = {
        "navigation_layout": {
            "name": "Navigation & Layout",
            "description": "Navigation menus, headers, footers, breadcrumbs, page structure elements"
        },
        "authentication_account": {
            "name": "Authentication & User Account",
            "description": "Login, registration, user profile, account settings, authentication forms"
        },
        "search_filters": {
            "name": "Search & Filters",
            "description": "Search bars, filter options, sorting controls, search results"
        },
        "category_listing": {
            "name": "Category & Product Listing Pages",
            "description": "Product lists, category pages, pagination, product cards, listing controls"
        },
        "product_details": {
            "name": "Product Details",
            "description": "Product pages, specifications, reviews, ratings, add to cart, product images"
        },
        "support_misc": {
            "name": "Support & Miscellaneous",
            "description": "Help, contact, customer service, notifications, alerts, other elements"
        }
    }
    
    def __init__(self):
        """
        Initialize the categorizer with Groq client.
        """
        self.api_key = os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found in environment variables")
        
        self.client = Groq(api_key=self.api_key)
        print("✅ Groq client initialized successfully")
    
    def create_categorization_prompt(self, selectors: Dict) -> str:
        """
        Create a detailed prompt for Groq to categorize selectors.
        
        Args:
            selectors (Dict): Extracted selectors data
            
        Returns:
            str: Formatted prompt for Groq
        """
        
        # Prepare selector samples for analysis
        selector_samples = []
        
        # Include various selector types with context
        selector_types = [
            ("id_selectors", "ID"),
            ("class_selectors", "Class"), 
            ("name_selectors", "Name"),
            ("input_selectors", "Input"),
            ("button_selectors", "Button"),
            ("link_selectors", "Link"),
            ("form_selectors", "Form")
        ]
        
        for selector_type, type_name in selector_types:
            if selector_type in selectors and selectors[selector_type]:
                # Take first 10 items of each type
                items = selectors[selector_type][:10]
                for item in items:
                    if isinstance(item, dict):
                        selector_info = {
                            "type": type_name,
                            "selector": item.get("selector", "N/A"),
                            "tag": item.get("tag", "N/A"),
                            "text": item.get("text_content", item.get("text", ""))[:100],
                            "additional_info": {}
                        }
                        
                        # Add type-specific information
                        if selector_type == "input_selectors":
                            selector_info["additional_info"] = {
                                "input_type": item.get("type", ""),
                                "name": item.get("name", ""),
                                "placeholder": item.get("placeholder", "")
                            }
                        elif selector_type == "button_selectors":
                            selector_info["additional_info"] = {
                                "button_type": item.get("type", ""),
                                "button_text": item.get("text", "")
                            }
                        elif selector_type == "link_selectors":
                            selector_info["additional_info"] = {
                                "href": item.get("href", "")[:100]
                            }
                        
                        selector_samples.append(selector_info)
        
        # Limit total samples to avoid token limits
        selector_samples = selector_samples[:50]
        
        prompt = f"""
You are an expert web scraper and UI/UX analyst. Analyze the following CSS selectors extracted from a website and categorize each one into exactly ONE of these categories:

CATEGORIES (use these exact keys in your response):
1. "navigation_layout" - Navigation menus, headers, footers, breadcrumbs, page structure elements, layout components
2. "authentication_account" - Login forms, registration, user profile, account settings, sign-in/sign-up elements
3. "search_filters" - Search bars, filter controls, sorting options, search results, query inputs
4. "category_listing" - Product lists, category pages, pagination, product cards, listing grids, product collections
5. "product_details" - Individual product pages, specifications, reviews, ratings, add to cart buttons, product images
6. "support_misc" - Help sections, contact forms, customer service, notifications, alerts, other miscellaneous elements

SELECTOR DATA FROM WEBSITE:
Website URL: {selectors.get('statistics', {}).get('url', 'Unknown')}
Total Elements: {selectors.get('statistics', {}).get('total_elements', 0)}

SELECTORS TO CATEGORIZE:
{json.dumps(selector_samples, indent=2)}

INSTRUCTIONS:
1. Analyze each selector based on its CSS selector, HTML tag, text content, and additional context
2. Consider common web patterns and naming conventions
3. Look for keywords in selectors, classes, IDs, and text that indicate functionality
4. Categorize based on the PRIMARY purpose of the element
5. When in doubt between categories, choose the most specific match

OUTPUT FORMAT (JSON only, no explanation text):
{{
    "categorized_selectors": {{
        "navigation_layout": [
            {{"selector": "selector_string", "confidence": 0.85, "reason": "brief reason"}}
        ],
        "authentication_account": [
            {{"selector": "selector_string", "confidence": 0.90, "reason": "brief reason"}}
        ],
        "search_filters": [
            {{"selector": "selector_string", "confidence": 0.95, "reason": "brief reason"}}
        ],
        "category_listing": [
            {{"selector": "selector_string", "confidence": 0.80, "reason": "brief reason"}}
        ],
        "product_details": [
            {{"selector": "selector_string", "confidence": 0.88, "reason": "brief reason"}}
        ],
        "support_misc": [
            {{"selector": "selector_string", "confidence": 0.75, "reason": "brief reason"}}
        ]
    }},
    "summary": {{
        "total_categorized": 0,
        "category_counts": {{
            "navigation_layout": 0,
            "authentication_account": 0,
            "search_filters": 0,
            "category_listing": 0,
            "product_details": 0,
            "support_misc": 0
        }},
        "average_confidence": 0.0
    }}
}}

Provide only the JSON response, no additional text.
"""
        return prompt
    
    def categorize_selectors_with_groq(self, selectors: Dict) -> Dict:
        """
        Use Groq AI to categorize selectors.
        
        Args:
            selectors (Dict): Extracted selectors data
            
        Returns:
            Dict: Categorized selectors
        """
        print("🤖 Categorizing selectors with Groq AI...")
        
        try:
            # Create the prompt
            prompt = self.create_categorization_prompt(selectors)
            
            # Call Groq API
            response = self.client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {
                        "role": "system", 
                        "content": "You are an expert web scraper and UI analyst. Respond only with valid JSON."
                    },
                    {
                        "role": "user", 
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=4000,
                timeout=60
            )
            
            # Parse the response
            response_content = response.choices[0].message.content.strip()
            
            # Clean up the response (remove any markdown formatting)
            if response_content.startswith("```json"):
                response_content = response_content[7:]
            if response_content.endswith("```"):
                response_content = response_content[:-3]
            
            categorized_data = json.loads(response_content)
            
            print("✅ Selectors categorized successfully")
            return categorized_data
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Raw response: {response_content[:500]}...")
            return self.create_fallback_categorization(selectors)
            
        except Exception as e:
            print(f"❌ Groq API error: {e}")
            return self.create_fallback_categorization(selectors)
    
    def create_fallback_categorization(self, selectors: Dict) -> Dict:
        """
        Create a basic rule-based categorization as fallback.
        
        Args:
            selectors (Dict): Original selectors
            
        Returns:
            Dict: Basic categorized selectors
        """
        print("🔄 Using fallback rule-based categorization...")
        
        categorized = {
            "categorized_selectors": {
                "navigation_layout": [],
                "authentication_account": [],
                "search_filters": [],
                "category_listing": [],
                "product_details": [],
                "support_misc": []
            },
            "summary": {
                "total_categorized": 0,
                "category_counts": {},
                "average_confidence": 0.6,
                "method": "fallback_rules"
            }
        }
        
        # Simple rule-based categorization
        all_selectors = []
        
        # Collect all selectors
        for selector_type in ["id_selectors", "class_selectors", "name_selectors"]:
            if selector_type in selectors:
                for item in selectors[selector_type]:
                    if isinstance(item, dict) and "selector" in item:
                        all_selectors.append(item["selector"])
        
        # Rule-based categorization
        for selector in all_selectors:
            selector_lower = selector.lower()
            
            # Navigation & Layout
            if any(keyword in selector_lower for keyword in [
                "nav", "menu", "header", "footer", "breadcrumb", "sidebar", "main", "banner"
            ]):
                categorized["categorized_selectors"]["navigation_layout"].append({
                    "selector": selector,
                    "confidence": 0.7,
                    "reason": "Contains navigation/layout keywords"
                })
            
            # Authentication & Account
            elif any(keyword in selector_lower for keyword in [
                "login", "signin", "signup", "register", "auth", "account", "user", "profile", "password"
            ]):
                categorized["categorized_selectors"]["authentication_account"].append({
                    "selector": selector,
                    "confidence": 0.8,
                    "reason": "Contains authentication keywords"
                })
            
            # Search & Filters
            elif any(keyword in selector_lower for keyword in [
                "search", "filter", "sort", "query", "find"
            ]):
                categorized["categorized_selectors"]["search_filters"].append({
                    "selector": selector,
                    "confidence": 0.8,
                    "reason": "Contains search/filter keywords"
                })
            
            # Product Details
            elif any(keyword in selector_lower for keyword in [
                "product", "item", "detail", "review", "rating", "cart", "buy", "price"
            ]):
                categorized["categorized_selectors"]["product_details"].append({
                    "selector": selector,
                    "confidence": 0.7,
                    "reason": "Contains product-related keywords"
                })
            
            # Support & Misc (default)
            else:
                categorized["categorized_selectors"]["support_misc"].append({
                    "selector": selector,
                    "confidence": 0.5,
                    "reason": "Default category"
                })
        
        # Update summary
        for category in categorized["categorized_selectors"]:
            count = len(categorized["categorized_selectors"][category])
            categorized["summary"]["category_counts"][category] = count
            categorized["summary"]["total_categorized"] += count
        
        return categorized
    
    def process_selector_file(self, selector_file_path: str, output_file_path: str = None) -> Dict:
        """
        Process a selector file and categorize its contents.
        
        Args:
            selector_file_path (str): Path to the selector JSON file
            output_file_path (str): Optional custom output path
            
        Returns:
            Dict: Processing result
        """
        print(f"📂 Processing selector file: {selector_file_path}")
        
        # Load selectors
        try:
            with open(selector_file_path, 'r', encoding='utf-8') as f:
                selectors = json.load(f)
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to load selector file: {e}",
                "file_path": selector_file_path
            }
        
        # Categorize selectors
        categorized_data = self.categorize_selectors_with_groq(selectors)
        
        # Create enhanced output
        output_data = {
            "metadata": {
                "original_file": selector_file_path,
                "categorization_timestamp": datetime.now().isoformat(),
                "original_url": selectors.get("statistics", {}).get("url", "Unknown"),
                "total_original_selectors": {
                    "id_selectors": len(selectors.get("id_selectors", [])),
                    "class_selectors": len(selectors.get("class_selectors", [])),
                    "name_selectors": len(selectors.get("name_selectors", [])),
                    "input_selectors": len(selectors.get("input_selectors", [])),
                    "button_selectors": len(selectors.get("button_selectors", [])),
                    "link_selectors": len(selectors.get("link_selectors", [])),
                    "form_selectors": len(selectors.get("form_selectors", []))
                }
            },
            "categories": self.CATEGORIES,
            "categorized_selectors": categorized_data.get("categorized_selectors", {}),
            "categorization_summary": categorized_data.get("summary", {}),
            "original_selectors": selectors  # Keep original data for reference
        }
        
        # Generate output file path if not provided
        if not output_file_path:
            base_name = os.path.splitext(os.path.basename(selector_file_path))[0]
            output_dir = os.path.join(os.path.dirname(selector_file_path), "..", "categorized_selectors")
            os.makedirs(output_dir, exist_ok=True)
            output_file_path = os.path.join(output_dir, f"{base_name}_categorized.json")
        
        # Save categorized results
        try:
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=4, ensure_ascii=False)
            
            print(f"💾 Categorized selectors saved to: {output_file_path}")
            
            return {
                "success": True,
                "input_file": selector_file_path,
                "output_file": output_file_path,
                "categorization_summary": categorized_data.get("summary", {}),
                "categories_found": list(categorized_data.get("categorized_selectors", {}).keys())
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to save categorized file: {e}",
                "input_file": selector_file_path
            }
    
    def batch_categorize_selectors(self, selector_directory: str) -> List[Dict]:
        """
        Categorize all selector files in a directory.
        
        Args:
            selector_directory (str): Directory containing selector JSON files
            
        Returns:
            List[Dict]: Results for each file processed
        """
        print(f"📁 Batch processing selector files in: {selector_directory}")
        
        results = []
        
        # Find all JSON files in the directory
        json_files = [f for f in os.listdir(selector_directory) if f.endswith('.json')]
        
        print(f"Found {len(json_files)} selector files to process")
        
        for i, filename in enumerate(json_files, 1):
            file_path = os.path.join(selector_directory, filename)
            print(f"\n📄 Processing {i}/{len(json_files)}: {filename}")
            
            result = self.process_selector_file(file_path)
            results.append(result)
            
            # Add delay between requests to be respectful to API
            if i < len(json_files):
                time.sleep(2)
        
        return results
    
    def print_categorization_summary(self, results: List[Dict]):
        """
        Print a summary of batch categorization results.
        
        Args:
            results (List[Dict]): Results from batch processing
        """
        successful = [r for r in results if r.get("success", False)]
        failed = [r for r in results if not r.get("success", False)]
        
        print(f"\n" + "="*60)
        print(f"📊 BATCH CATEGORIZATION SUMMARY")
        print(f"="*60)
        print(f"Total Files: {len(results)}")
        print(f"Successful: {len(successful)}")
        print(f"Failed: {len(failed)}")
        
        if successful:
            print(f"\n✅ SUCCESSFUL CATEGORIZATIONS:")
            total_by_category = {category: 0 for category in self.CATEGORIES}
            
            for result in successful:
                summary = result.get("categorization_summary", {})
                category_counts = summary.get("category_counts", {})
                total_categorized = summary.get("total_categorized", 0)
                
                filename = os.path.basename(result["input_file"])
                print(f"   📄 {filename}: {total_categorized} selectors categorized")
                
                for category, count in category_counts.items():
                    if count > 0:
                        total_by_category[category] += count
                        print(f"      - {self.CATEGORIES.get(category, {}).get('name', category)}: {count}")
            
            print(f"\n📈 OVERALL CATEGORY DISTRIBUTION:")
            for category_key, total_count in total_by_category.items():
                if total_count > 0:
                    category_name = self.CATEGORIES.get(category_key, {}).get("name", category_key)
                    print(f"   {category_name}: {total_count}")
        
        if failed:
            print(f"\n❌ FAILED CATEGORIZATIONS:")
            for result in failed:
                filename = os.path.basename(result.get("input_file", "unknown"))
                error = result.get("error", "Unknown error")
                print(f"   📄 {filename}: {error}")
        
        print(f"="*60)


def main():
    """
    Main function to demonstrate selector categorization.
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python selector_categorizer.py <selector_file.json>")
        print("  python selector_categorizer.py <selector_directory>")
        print("  python selector_categorizer.py --batch <selector_directory>")
        print("\nExamples:")
        print("  python selector_categorizer.py ../extracted_data/selectors/selectors_example_com_123.json")
        print("  python selector_categorizer.py --batch ../extracted_data/selectors/")
        sys.exit(1)
    
    # Initialize categorizer
    try:
        categorizer = SelectorCategorizer()
    except Exception as e:
        print(f"❌ Failed to initialize categorizer: {e}")
        sys.exit(1)
    
    # Process command line arguments
    if sys.argv[1] == "--batch":
        if len(sys.argv) < 3:
            print("❌ Please provide directory path for batch processing")
            sys.exit(1)
        
        directory_path = sys.argv[2]
        if not os.path.isdir(directory_path):
            print(f"❌ Directory not found: {directory_path}")
            sys.exit(1)
        
        # Batch process
        results = categorizer.batch_categorize_selectors(directory_path)
        categorizer.print_categorization_summary(results)
        
    else:
        file_path = sys.argv[1]
        
        if os.path.isfile(file_path):
            # Single file processing
            result = categorizer.process_selector_file(file_path)
            
            if result["success"]:
                print(f"\n✅ SUCCESS!")
                print(f"Input file: {result['input_file']}")
                print(f"Output file: {result['output_file']}")
                print(f"Categories found: {', '.join(result['categories_found'])}")
                
                summary = result["categorization_summary"]
                print(f"Total selectors categorized: {summary.get('total_categorized', 0)}")
            else:
                print(f"\n❌ FAILED!")
                print(f"Error: {result['error']}")
        
        elif os.path.isdir(file_path):
            # Directory processing
            results = categorizer.batch_categorize_selectors(file_path)
            categorizer.print_categorization_summary(results)
        
        else:
            print(f"❌ File or directory not found: {file_path}")
            sys.exit(1)


if __name__ == "__main__":
    main()