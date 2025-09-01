#!/usr/bin/env python3
"""
Action Handler Script for Processing Multiple Action Types

This script handles various actions including:
- 'GOTO URL : <url>' - Navigate to URL and extract selectors
- 'CLICK BUTTON <button>' - Click on specified button element

Actions supported:
1. Parsing action commands
2. Navigating to URLs
3. Clicking buttons/elements
4. Extracting selectors using BeautifulSoup
5. Saving results to organized files
6. Maintaining a mapping of actions to results
"""

import os
import json
import re
import time
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse
import hashlib

# Import browser automation
try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("⚠️ Playwright not available. CLICK BUTTON actions will be limited.")

# Import our selector extraction functionality
from test_extract_selector import fetch_website_content, extract_all_selectors, save_selectors_to_file


class ActionHandler:
    """
    Handles multiple action types including GOTO URL and CLICK BUTTON actions.
    Manages browser automation, selector extraction, and action tracking workflow.
    """
    
    def __init__(self, base_output_dir: str = "../extracted_data", headless: bool = True):
        """
        Initialize the action handler.
        
        Args:
            base_output_dir (str): Base directory for storing extracted data
            headless (bool): Whether to run browser in headless mode
        """
        self.base_output_dir = base_output_dir
        self.selectors_dir = os.path.join(base_output_dir, "selectors")
        self.actions_mapping_file = os.path.join(base_output_dir, "actions_mapping.json")
        self.headless = headless
        
        # Browser state tracking
        self.browser = None
        self.page = None
        self.current_url = None
        
        # Create directories if they don't exist
        os.makedirs(self.selectors_dir, exist_ok=True)
        os.makedirs(base_output_dir, exist_ok=True)
        
        # Load existing actions mapping or create new one
        self.actions_mapping = self.load_actions_mapping()
    
    def load_actions_mapping(self) -> Dict:
        """
        Load existing actions mapping from file or create new one.
        
        Returns:
            Dict: Actions mapping dictionary
        """
        if os.path.exists(self.actions_mapping_file):
            try:
                with open(self.actions_mapping_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading actions mapping: {e}")
                return self.create_empty_mapping()
        else:
            return self.create_empty_mapping()
    
    def create_empty_mapping(self) -> Dict:
        """
        Create an empty actions mapping structure.
        
        Returns:
            Dict: Empty mapping structure
        """
        return {
            "metadata": {
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "total_actions": 0
            },
            "actions": {}
        }
    
    def save_actions_mapping(self):
        """
        Save the actions mapping to file.
        """
        try:
            self.actions_mapping["metadata"]["last_updated"] = datetime.now().isoformat()
            with open(self.actions_mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.actions_mapping, f, indent=4, ensure_ascii=False)
            print(f"📄 Actions mapping updated: {self.actions_mapping_file}")
        except Exception as e:
            print(f"❌ Error saving actions mapping: {e}")
    
    def parse_goto_action(self, action_string: str) -> Optional[str]:
        """
        Parse a GOTO URL action string to extract the URL.
        
        Args:
            action_string (str): Action string like 'GOTO URL : https://example.com'
            
        Returns:
            Optional[str]: Extracted URL or None if parsing fails
        """
        # Clean the action string
        action_string = action_string.strip()
        
        # Pattern to match GOTO URL actions (case insensitive)
        patterns = [
            r'GOTO\s+URL\s*:\s*(.+)',
            r'GO\s+TO\s+URL\s*:\s*(.+)',
            r'NAVIGATE\s+TO\s*:\s*(.+)',
            r'VISIT\s*:\s*(.+)'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, action_string, re.IGNORECASE)
            if match:
                url = match.group(1).strip()
                # Remove quotes if present
                url = url.strip('"\'')
                return url
        
        # If no pattern matches, check if it's just a URL
        if action_string.startswith(('http://', 'https://')):
            return action_string
        
        return None
    
    def parse_click_button_action(self, action_string: str) -> Optional[str]:
        """
        Parse a CLICK BUTTON action string to extract the button identifier.
        
        Args:
            action_string (str): Action string like 'CLICK BUTTON #submit-btn'
            
        Returns:
            Optional[str]: Extracted button identifier or None if parsing fails
        """
        # Clean the action string
        action_string = action_string.strip()
        
        # Pattern to match CLICK BUTTON actions (case insensitive)
        patterns = [
            r'CLICK\s+BUTTON\s+(.+)',
            r'CLICK\s+(.+)',
            r'PRESS\s+BUTTON\s+(.+)',
            r'PRESS\s+(.+)',
            r'TAP\s+(.+)'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, action_string, re.IGNORECASE)
            if match:
                button_selector = match.group(1).strip()
                # Remove quotes if present
                button_selector = button_selector.strip('"\'')
                return button_selector
        
        return None
    
    def parse_action_type(self, action_string: str) -> str:
        """
        Determine the type of action from the action string.
        
        Args:
            action_string (str): The action string to analyze
            
        Returns:
            str: Action type ('goto_url', 'click_button', 'unknown')
        """
        action_string = action_string.strip().upper()
        
        # Check for GOTO URL actions
        if any(keyword in action_string for keyword in ['GOTO URL', 'GO TO URL', 'NAVIGATE TO', 'VISIT']):
            return 'goto_url'
        elif action_string.startswith(('HTTP://', 'HTTPS://')):
            return 'goto_url'
        
        # Check for CLICK BUTTON actions
        elif any(keyword in action_string for keyword in ['CLICK BUTTON', 'CLICK', 'PRESS BUTTON', 'PRESS', 'TAP']):
            return 'click_button'
        
        return 'unknown'
    
    def validate_url(self, url: str) -> bool:
        """
        Validate if the URL is properly formatted.
        
        Args:
            url (str): URL to validate
            
        Returns:
            bool: True if URL is valid
        """
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False
    
    def generate_selector_filename(self, url: str) -> str:
        """
        Generate a unique filename for storing selectors based on URL.
        
        Args:
            url (str): The URL being processed
            
        Returns:
            str: Generated filename
        """
        # Parse URL to get domain
        parsed = urlparse(url)
        domain = parsed.netloc.replace('.', '_').replace(':', '_')
        
        # Create a hash of the full URL for uniqueness
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        
        # Generate timestamp
        timestamp = int(time.time())
        
        # Create filename
        filename = f"selectors_{domain}_{timestamp}_{url_hash}.json"
        return os.path.join(self.selectors_dir, filename)
    
    async def start_browser(self):
        """
        Start the browser session for interactive actions.
        """
        if not PLAYWRIGHT_AVAILABLE:
            raise Exception("Playwright not available. Install with: pip install playwright")
        
        if self.browser is None:
            print("🚀 Starting browser...")
            playwright = await async_playwright().start()
            self.browser = await playwright.chromium.launch(headless=self.headless, slow_mo=1000)
            self.page = await self.browser.new_page()
            self.page.set_default_timeout(15000)
            print("✅ Browser started successfully")
    
    async def close_browser(self):
        """
        Close the browser session.
        """
        if self.browser:
            print("🔒 Closing browser...")
            await self.browser.close()
            self.browser = None
            self.page = None
            self.current_url = None
            print("✅ Browser closed")
    
    async def navigate_to_url(self, url: str) -> bool:
        """
        Navigate to a URL using the browser.
        
        Args:
            url (str): URL to navigate to
            
        Returns:
            bool: True if navigation successful
        """
        try:
            await self.start_browser()
            print(f"🌐 Navigating to: {url}")
            await self.page.goto(url)
            await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            self.current_url = url
            print(f"✅ Successfully navigated to: {url}")
            return True
        except Exception as e:
            print(f"❌ Navigation failed: {e}")
            return False
    
    async def find_button_selectors(self, button_identifier: str) -> List[str]:
        """
        Find possible selectors for a button based on the identifier.
        
        Args:
            button_identifier (str): Button identifier (text, selector, etc.)
            
        Returns:
            List[str]: List of possible selectors to try
        """
        if not self.page:
            return []
        
        selectors_to_try = []
        
        # If it looks like a CSS selector, use it directly
        if any(char in button_identifier for char in ['#', '.', '[', ']']):
            selectors_to_try.append(button_identifier)
        
        # Try common button selectors
        selectors_to_try.extend([
            f"button:has-text('{button_identifier}')",
            f"input[type='submit'][value='{button_identifier}']",
            f"input[type='button'][value='{button_identifier}']",
            f"[aria-label='{button_identifier}']",
            f"[title='{button_identifier}']",
            f"#{button_identifier}",
            f".{button_identifier}",
            f"button[name='{button_identifier}']",
            f"input[name='{button_identifier}']",
            f"[data-testid='{button_identifier}']",
            f"[data-hook='{button_identifier}']"
        ])
        
        # Try partial text matches
        selectors_to_try.extend([
            f"button:has-text('{button_identifier.lower()}')",
            f"button:has-text('{button_identifier.upper()}')",
            f"button:has-text('{button_identifier.title()}')"
        ])
        
        return selectors_to_try
    
    async def click_button(self, button_identifier: str) -> Dict:
        """
        Click a button using various selector strategies.
        
        Args:
            button_identifier (str): Button identifier
            
        Returns:
            Dict: Result of the click action
        """
        if not self.page:
            return {
                "success": False,
                "error": "No browser page available. Navigate to a URL first."
            }
        
        print(f"🔍 Looking for button: {button_identifier}")
        
        # Get possible selectors
        selectors = await self.find_button_selectors(button_identifier)
        
        # Try each selector
        for selector in selectors:
            try:
                print(f"   Trying selector: {selector}")
                # Check if element exists
                element = await self.page.query_selector(selector)
                if element:
                    # Check if element is visible and clickable
                    is_visible = await element.is_visible()
                    is_enabled = await element.is_enabled()
                    
                    if is_visible and is_enabled:
                        print(f"✅ Found clickable button with selector: {selector}")
                        await element.click()
                        print(f"🎯 Successfully clicked button!")
                        
                        # Wait for potential page changes
                        await asyncio.sleep(2)
                        
                        return {
                            "success": True,
                            "selector_used": selector,
                            "button_identifier": button_identifier,
                            "current_url": self.page.url
                        }
                    else:
                        print(f"   Button found but not clickable (visible: {is_visible}, enabled: {is_enabled})")
                        
            except Exception as e:
                print(f"   Selector failed: {e}")
                continue
        
        return {
            "success": False,
            "error": f"Button '{button_identifier}' not found or not clickable",
            "selectors_tried": selectors
        }
    
    async def process_click_button_action(self, action_string: str) -> Dict:
        """
        Process a CLICK BUTTON action completely.
        
        Args:
            action_string (str): The action string to process
            
        Returns:
            Dict: Result of the action processing
        """
        print(f"🎯 Processing action: {action_string}")
        
        # Parse the action to extract button identifier
        button_identifier = self.parse_click_button_action(action_string)
        if not button_identifier:
            return {
                "success": False,
                "error": "Could not parse button identifier from action string",
                "action": action_string
            }
        
        print(f"🔘 Button identifier: {button_identifier}")
        
        # Check if we have a browser session
        if not self.page:
            return {
                "success": False,
                "error": "No active browser session. Navigate to a URL first.",
                "action": action_string,
                "button_identifier": button_identifier
            }
        
        try:
            # Click the button
            click_result = await self.click_button(button_identifier)
            
            # Create action record
            action_id = hashlib.md5(f"{action_string}_{time.time()}".encode()).hexdigest()
            action_record = {
                "action_id": action_id,
                "action_string": action_string,
                "action_type": "click_button",
                "button_identifier": button_identifier,
                "current_url_before": self.current_url,
                "current_url_after": self.page.url if self.page else None,
                "timestamp": datetime.now().isoformat(),
                "status": "completed" if click_result["success"] else "failed",
                "click_result": click_result
            }
            
            # Add to actions mapping
            self.actions_mapping["actions"][action_id] = action_record
            self.actions_mapping["metadata"]["total_actions"] += 1
            
            # Save actions mapping
            self.save_actions_mapping()
            
            if click_result["success"]:
                print(f"✅ Action completed successfully!")
                print(f"🔗 Action ID: {action_id}")
            else:
                print(f"❌ Action failed: {click_result['error']}")
            
            return {
                "success": click_result["success"],
                "action_id": action_id,
                "action": action_string,
                "button_identifier": button_identifier,
                "selector_used": click_result.get("selector_used"),
                "error": click_result.get("error"),
                "current_url": self.page.url if self.page else None
            }
            
        except Exception as e:
            error_record = {
                "action_string": action_string,
                "action_type": "click_button",
                "button_identifier": button_identifier,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "status": "failed"
            }
            
            # Still save the failed action for tracking
            action_id = hashlib.md5(f"{action_string}_{time.time()}_error".encode()).hexdigest()
            self.actions_mapping["actions"][action_id] = error_record
            self.save_actions_mapping()
            
            return {
                "success": False,
                "error": str(e),
                "action": action_string,
                "button_identifier": button_identifier,
                "action_id": action_id
            }
    
    def process_goto_action(self, action_string: str) -> Dict:
        """
        Process a GOTO URL action completely.
        
        Args:
            action_string (str): The action string to process
            
        Returns:
            Dict: Result of the action processing
        """
        print(f"🎯 Processing action: {action_string}")
        
        # Parse the action to extract URL
        url = self.parse_goto_action(action_string)
        if not url:
            return {
                "success": False,
                "error": "Could not parse URL from action string",
                "action": action_string
            }
        
        print(f"📍 Extracted URL: {url}")
        
        # Validate URL
        if not self.validate_url(url):
            return {
                "success": False,
                "error": "Invalid URL format",
                "action": action_string,
                "url": url
            }
        
        try:
            # Fetch website content
            print(f"🌐 Fetching content from: {url}")
            html_content = fetch_website_content(url)
            
            # Extract selectors
            print(f"🔍 Extracting selectors...")
            selectors = extract_all_selectors(html_content, url)
            
            # Generate filename for selectors
            selector_file_path = self.generate_selector_filename(url)
            
            # Save selectors to file
            print(f"💾 Saving selectors...")
            save_selectors_to_file(selectors, selector_file_path)
            
            # Create action record
            action_id = hashlib.md5(f"{action_string}_{time.time()}".encode()).hexdigest()
            action_record = {
                "action_id": action_id,
                "action_string": action_string,
                "url": url,
                "selector_file_path": os.path.relpath(selector_file_path, self.base_output_dir),
                "absolute_selector_file_path": os.path.abspath(selector_file_path),
                "timestamp": datetime.now().isoformat(),
                "status": "completed",
                "statistics": selectors.get("statistics", {}),
                "total_selectors": {
                    "id_selectors": len(selectors.get("id_selectors", [])),
                    "class_selectors": len(selectors.get("class_selectors", [])),
                    "name_selectors": len(selectors.get("name_selectors", [])),
                    "input_selectors": len(selectors.get("input_selectors", [])),
                    "button_selectors": len(selectors.get("button_selectors", [])),
                    "link_selectors": len(selectors.get("link_selectors", [])),
                    "form_selectors": len(selectors.get("form_selectors", [])),
                    "attribute_selectors": len(selectors.get("attribute_selectors", [])),
                    "combined_patterns": len(selectors.get("combined_selectors", []))
                }
            }
            
            # Add to actions mapping
            self.actions_mapping["actions"][action_id] = action_record
            self.actions_mapping["metadata"]["total_actions"] += 1
            
            # Save actions mapping
            self.save_actions_mapping()
            
            print(f"✅ Action completed successfully!")
            print(f"📂 Selectors saved to: {selector_file_path}")
            print(f"🔗 Action ID: {action_id}")
            
            return {
                "success": True,
                "action_id": action_id,
                "action": action_string,
                "url": url,
                "selector_file_path": selector_file_path,
                "relative_path": os.path.relpath(selector_file_path, self.base_output_dir),
                "selectors_count": action_record["total_selectors"]
            }
            
        except Exception as e:
            error_record = {
                "action_string": action_string,
                "url": url,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "status": "failed"
            }
            
            # Still save the failed action for tracking
            action_id = hashlib.md5(f"{action_string}_{time.time()}_error".encode()).hexdigest()
            self.actions_mapping["actions"][action_id] = error_record
            self.save_actions_mapping()
            
            return {
                "success": False,
                "error": str(e),
                "action": action_string,
                "url": url,
                "action_id": action_id
            }
    
    def get_action_history(self) -> List[Dict]:
        """
        Get history of all processed actions.
        
        Returns:
            List[Dict]: List of action records
        """
        return list(self.actions_mapping.get("actions", {}).values())
    
    def get_action_by_id(self, action_id: str) -> Optional[Dict]:
        """
        Get a specific action record by ID.
        
        Args:
            action_id (str): The action ID to look up
            
        Returns:
            Optional[Dict]: Action record or None if not found
        """
        return self.actions_mapping.get("actions", {}).get(action_id)
    
    def print_summary(self):
        """
        Print a summary of all processed actions.
        """
        total_actions = self.actions_mapping["metadata"]["total_actions"]
        successful_actions = len([a for a in self.actions_mapping["actions"].values() 
                                if a.get("status") == "completed"])
        failed_actions = total_actions - successful_actions
        
        print(f"\n" + "="*60)
        print(f"📊 ACTION HANDLER SUMMARY")
        print(f"="*60)
        print(f"Total Actions Processed: {total_actions}")
        print(f"Successful Actions: {successful_actions}")
        print(f"Failed Actions: {failed_actions}")
        print(f"Actions Mapping File: {self.actions_mapping_file}")
        print(f"Selectors Directory: {self.selectors_dir}")
        
        if successful_actions > 0:
            print(f"\n🎯 RECENT SUCCESSFUL ACTIONS:")
            recent_actions = sorted(
                [a for a in self.actions_mapping["actions"].values() if a.get("status") == "completed"],
                key=lambda x: x.get("timestamp", ""),
                reverse=True
            )[:5]
            
            for i, action in enumerate(recent_actions, 1):
                print(f"{i}. {action['action_string']}")
                print(f"   URL: {action['url']}")
                print(f"   File: {action.get('relative_path', 'N/A')}")
                print(f"   Selectors: {sum(action.get('total_selectors', {}).values())}")
        
        print("="*60)
    
    async def process_action(self, action_string: str) -> Dict:
        """
        Process any type of action by dispatching to the appropriate handler.
        
        Args:
            action_string (str): The action string to process
            
        Returns:
            Dict: Result of the action processing
        """
        action_type = self.parse_action_type(action_string)
        
        if action_type == 'goto_url':
            return self.process_goto_action(action_string)
        elif action_type == 'click_button':
            return await self.process_click_button_action(action_string)
        else:
            return {
                "success": False,
                "error": f"Unknown action type: {action_type}",
                "action": action_string,
                "supported_actions": ["GOTO URL : <url>", "CLICK BUTTON <button>"]
            }
    
    def __del__(self):
        """
        Cleanup method to ensure browser is closed.
        """
        if self.browser and asyncio.get_event_loop().is_running():
            asyncio.create_task(self.close_browser())


async def main_async():
    """
    Main async function to handle both GOTO URL and CLICK BUTTON actions.
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python action_handler.py \"GOTO URL : <url>\"")
        print("  python action_handler.py \"CLICK BUTTON <button>\"")
        print("\nExamples:")
        print("  python action_handler.py \"GOTO URL : https://example.com\"")
        print("  python action_handler.py \"CLICK BUTTON Submit\"")
        print("  python action_handler.py \"CLICK BUTTON #login-btn\"")
        print("  python action_handler.py \"CLICK .search-button\"")
        sys.exit(1)
    
    action_string = " ".join(sys.argv[1:])
    
    # Initialize action handler
    handler = ActionHandler(headless=False)  # Show browser for click actions
    
    try:
        # Process the action
        result = await handler.process_action(action_string)
        
        if result["success"]:
            print(f"\n✅ SUCCESS!")
            print(f"Action ID: {result['action_id']}")
            
            # Different success messages for different action types
            if result.get('selectors_count'):
                print(f"Selectors saved to: {result['relative_path']}")
                print(f"Total selectors extracted: {sum(result['selectors_count'].values())}")
            elif result.get('selector_used'):
                print(f"Button clicked with selector: {result['selector_used']}")
                print(f"Current URL: {result.get('current_url', 'N/A')}")
        else:
            print(f"\n❌ FAILED!")
            print(f"Error: {result['error']}")
            if 'supported_actions' in result:
                print(f"Supported actions: {result['supported_actions']}")
        
        # Print summary
        handler.print_summary()
    
    finally:
        # Ensure browser is closed
        await handler.close_browser()


def main():
    """
    Synchronous main function that runs the async main.
    """
    asyncio.run(main_async())


if __name__ == "__main__":
    main()