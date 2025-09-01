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
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

class SelectorCategorizer:
    """
    Categorizes extracted selectors using configurable AI providers (Groq or Local LM) into predefined categories.
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
    
    def __init__(self, provider: str = "local", local_model_url: str = "http://localhost:1234", 
                 local_model_name: str = "openai/gpt-oss-20b", timeout: float = 120.0):
        """
        Initialize the categorizer with specified AI provider.
        
        Args:
            provider: AI provider to use ("groq" or "local")
            local_model_url: URL for local LM server (when provider="local")
            local_model_name: Model name for local LM (when provider="local")
            timeout: Request timeout in seconds
        """
        self.provider = provider.lower()
        self.local_model_url = local_model_url
        self.local_model_name = local_model_name
        self.timeout = timeout
        
        if self.provider == "groq":
            self.api_key = os.getenv("GROQ_API_KEY")
            if not self.api_key:
                raise ValueError("GROQ_API_KEY not found in environment variables")
            
            self.client = Groq(api_key=self.api_key)
            print("✅ Groq client initialized successfully")
        
        elif self.provider == "local":
            print(f"✅ Local LM client initialized for {local_model_url}")
        
        else:
            raise ValueError(f"Unsupported provider: {provider}. Use 'groq' or 'local'")
    
    async def ask_local_model(self, prompt: str, system_prompt: str) -> str:
        """
        Query local LM model using the same interface as test_lm_studio_model_conn.py
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            
        Returns:
            str: Model response content
        """
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            payload = {
                "model": self.local_model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 4000,
            }
            resp = await client.post(f"{self.local_model_url}/v1/chat/completions", json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
    
    def create_categorization_prompt(self, selector_batch: List) -> str:
        """
        Create a detailed prompt for AI to categorize a batch of selectors.
        
        Args:
            selector_batch (List): Batch of selectors to categorize
            
        Returns:
            str: Formatted prompt for AI
        """
        
        prompt = f""" SELECTORS TO CATEGORIZE:
        {json.dumps(selector_batch, indent=2)}
        """
        return prompt
    
    def prepare_all_selectors(self, selectors: Dict) -> List[Dict]:
        """
        Prepare all selectors from the input data into a flat list.
        
        Args:
            selectors (Dict): Extracted selectors data
            
        Returns:
            List[Dict]: All selectors with their metadata
        """
        all_selectors = []
        
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
                for item in selectors[selector_type]:
                    if isinstance(item, dict):
                        selector_info = {
                            "uuid": item.get("uuid", "N/A"),
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
                        
                        all_selectors.append(selector_info)
        
        return all_selectors
    
    def  get_system_role(self) -> str:
        """
        Get the system role description for the Groq prompt.
        
        Returns:
            str: System role description
        """
        return (
            """
                You are an expert web scraper and UI/UX analyst. Analyze the provided CSS selectors and categorize EACH selector into EXACTLY ONE of the following categories:

                CATEGORIES (use these exact keys in your response):
                1. "navigation_layout" - Headers, footers, menus, breadcrumbs, structural layout components
                2. "authentication_account" - Login, registration, user profile, account settings, authentication elements
                3. "search_filters" - Search bars, filters, sorting controls, query inputs
                4. "category_listing" - Category pages, product grids, product cards, listing containers, pagination
                5. "product_details" - Product page elements: specifications, reviews, ratings, add to cart, buy now, product images
                6. "support_misc" - Help, contact, customer service, notifications, alerts, miscellaneous site elements
                7. "uncategorized_selector" - Ambiguous or selectors that don’t clearly fit into any above category

                INSTRUCTIONS:
                1. Use selector name, HTML tag, attributes, and text content for classification.
                2. Apply common web conventions to infer intent (e.g., `#search-bar`, `.login-form`, `#product-grid`).
                3. Choose the PRIMARY function of the element; if unclear, use "uncategorized_selector".
                4. Assign a confidence score between 0 and 1 (two decimal places).
                5. Provide ONLY the required JSON format.

                OUTPUT FORMAT (strict JSON only, no extra text):
                [
                    { "category": "<category>", "uuid": "selector_uuid", "confidence": 0.85 }
                ]
        """
        )
    
    def categorize_selectors_with_ai(self, selectors: Dict) -> Dict:
        """
        Use configured AI provider to categorize selectors in batches with rate limiting.
        
        Args:
            selectors (Dict): Extracted selectors data
            
        Returns:
            Dict: Categorized selectors
        """
        provider_name = "Groq AI" if self.provider == "groq" else "openai/gpt-oss-20b"
        print(f"🤖 Categorizing selectors with {provider_name}...")
        
        # Prepare all selectors
        all_selectors = self.prepare_all_selectors(selectors)
        total_selectors = len(all_selectors)
        
        if total_selectors == 0:
            print("⚠️ No selectors found to categorize")
            return self.create_empty_categorization()
        
        print(f"📊 Total selectors to categorize: {total_selectors}")
        
        # Initialize simple result list
        final_result = []
        
        # Process in batches of 50
        batch_size = 40
        batches = [all_selectors[i:i + batch_size] for i in range(0, total_selectors, batch_size)]
        total_batches = len(batches)
        
        print(f"📦 Processing {total_batches} batches of up to {batch_size} selectors each")
        
        api_call_count = 0
        successful_batches = 0
        total_categorized_count = 0
        
        for batch_idx, batch in enumerate(batches, 1):
            print(f"\n🔄 Processing batch {batch_idx}/{total_batches} ({len(batch)} selectors)...")
            
            try:
                # Create the prompt for this batch
                system_role = self.get_system_role()
                prompt = self.create_categorization_prompt(batch)
                
                # Call AI provider
                if self.provider == "groq":
                    response = self.client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[
                            {
                                "role": "system", 
                                "content": system_role
                            },
                            {
                                "role": "user", 
                                "content": prompt
                            }
                        ],
                        temperature=1,
                        max_completion_tokens=8192,
                        top_p=1,
                        reasoning_effort="medium",
                        stream=True,
                        stop=None
                    )
                    response_content = response.choices[0].message.content.strip()
                
                elif self.provider == "local":
                    response_content = asyncio.run(self.ask_local_model(prompt, system_role))
                
                else:
                    raise ValueError(f"Unsupported provider: {self.provider}")
                
                api_call_count += 1
                
                # Clean up the response (remove any markdown formatting)
                if response_content.startswith("```json"):
                    response_content = response_content[7:]
                if response_content.endswith("```"):
                    response_content = response_content[:-3]
                
                batch_result = json.loads(response_content)
                
                # Process simple array format: [{"category": "...", "uuid": "...", "confidence": 0.85}]
                if isinstance(batch_result, list):
                    final_result.extend(batch_result)
                    total_categorized_count += len(batch_result)
                
                successful_batches += 1
                print(f"✅ Batch {batch_idx} processed successfully ({len(batch_result) if isinstance(batch_result, list) else 0} categorized)")
                
                # Rate limiting: sleep for 100 seconds after every 10 API calls
                if api_call_count % 10 == 0 and batch_idx < total_batches:
                    print(f"⏱️ Rate limiting: Sleeping for 100 seconds after {api_call_count} API calls...")
                    time.sleep(1)
                
                # Small delay between batches
                elif batch_idx < total_batches:
                    time.sleep(3)
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error in batch {batch_idx}: {e}")
                print(f"Raw response: {response_content[:200]}...")
                continue
                
            except Exception as e:
                print(f"❌ API error in batch {batch_idx}: {e}")
                continue
        
        print(f"\n🎉 Batch processing completed!")
        print(f"   Total batches: {total_batches}")
        print(f"   Successful batches: {successful_batches}")
        print(f"   Total selectors categorized: {total_categorized_count}")
        print(f"   API calls made: {api_call_count}")
        
        if successful_batches == 0:
            print("⚠️ No batches were successful, using fallback categorization")
            return self.create_fallback_categorization(selectors)
        
        return final_result
    
    def create_empty_categorization(self) -> List:
        """
        Create empty categorization structure.
        
        Returns:
            List: Empty list
        """
        return []
    
    def create_fallback_categorization(self, selectors: Dict) -> List:
        """
        Create a basic rule-based categorization as fallback.
        
        Args:
            selectors (Dict): Original selectors
            
        Returns:
            List: Basic categorized selectors
        """
        print("🔄 Using fallback rule-based categorization...")
        
        categorized = []
        
        # Simple rule-based categorization
        all_selectors = []
        
        # Collect all selectors with UUIDs
        for selector_type in ["id_selectors", "class_selectors", "name_selectors", "input_selectors", "button_selectors", "link_selectors", "form_selectors"]:
            if selector_type in selectors:
                for item in selectors[selector_type]:
                    if isinstance(item, dict) and "selector" in item:
                        all_selectors.append({
                            "uuid": item.get("uuid", "N/A"),
                            "selector": item["selector"]
                        })
        
        # Rule-based categorization
        for selector_item in all_selectors[:200]:  # Limit fallback to 200 items
            selector = selector_item["selector"]
            uuid = selector_item["uuid"]
            selector_lower = selector.lower()
            
            # Navigation & Layout
            if any(keyword in selector_lower for keyword in [
                "nav", "menu", "header", "footer", "breadcrumb", "sidebar", "main", "banner"
            ]):
                categorized.append({
                    "category": "navigation_layout",
                    "uuid": uuid,
                    "confidence": 0.7
                })
            
            # Authentication & Account
            elif any(keyword in selector_lower for keyword in [
                "login", "signin", "signup", "register", "auth", "account", "user", "profile", "password"
            ]):
                categorized.append({
                    "category": "authentication_account",
                    "uuid": uuid,
                    "confidence": 0.8
                })
            
            # Search & Filters
            elif any(keyword in selector_lower for keyword in [
                "search", "filter", "sort", "query", "find"
            ]):
                categorized.append({
                    "category": "search_filters",
                    "uuid": uuid,
                    "confidence": 0.8
                })
            
            # Product Details
            elif any(keyword in selector_lower for keyword in [
                "product", "item", "detail", "review", "rating", "cart", "buy", "price"
            ]):
                categorized.append({
                    "category": "product_details",
                    "uuid": uuid,
                    "confidence": 0.7
                })
            
            # Uncategorized (default)
            else:
                categorized.append({
                    "category": "uncategorized_selector",
                    "uuid": uuid,
                    "confidence": 0.3
                })
        
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
        categorized_data = self.categorize_selectors_with_ai(selectors)
        
        # Create simple output - just the array
        output_data = categorized_data
        
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
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Categorized selectors saved to: {output_file_path}")
            
            return {
                "success": True,
                "input_file": selector_file_path,
                "output_file": output_file_path,
                "total_categorized": len(categorized_data) if isinstance(categorized_data, list) else 0,
                "categories_found": []  # Empty list since we're using flat array format
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
                time.sleep(3)
        
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
    
    # Parse provider argument
    provider = "groq"  # default
    if "--provider" in sys.argv:
        provider_idx = sys.argv.index("--provider")
        if provider_idx + 1 < len(sys.argv):
            provider = sys.argv[provider_idx + 1]
            # Remove provider arguments from sys.argv for cleaner processing
            sys.argv.pop(provider_idx + 1)
            sys.argv.pop(provider_idx)
    
    # Initialize categorizer
    try:
        categorizer = SelectorCategorizer(provider=provider)
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
                print(f"Total selectors categorized: {result.get('total_categorized', 0)}")
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