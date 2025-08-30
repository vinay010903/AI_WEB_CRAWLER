#!/usr/bin/env python3
"""
Example Usage of the Action Handler System

This script demonstrates how to use the action handler system
to process GOTO URL actions and extract selectors.
"""

from action_handler import ActionHandler
from batch_action_processor import process_actions_from_list
import json


def example_single_action():
    """
    Example of processing a single GOTO URL action.
    """
    print("🔥 EXAMPLE 1: Single Action Processing")
    print("="*50)
    
    # Initialize the action handler
    handler = ActionHandler()
    
    # Process a single action
    action = "GOTO URL : https://example.com"
    result = handler.process_goto_action(action)
    
    if result["success"]:
        print(f"✅ Successfully processed: {action}")
        print(f"📄 Selectors file: {result['relative_path']}")
        print(f"🔢 Total selectors: {sum(result['selectors_count'].values())}")
    else:
        print(f"❌ Failed to process: {action}")
        print(f"Error: {result['error']}")
    
    # Show the action history
    print(f"\n📚 Action History:")
    history = handler.get_action_history()
    for i, action_record in enumerate(history[-3:], 1):  # Show last 3
        status = "✅" if action_record.get("status") == "completed" else "❌"
        print(f"{i}. {status} {action_record.get('action_string', 'N/A')}")


def example_batch_processing():
    """
    Example of processing multiple actions in batch.
    """
    print(f"\n🔥 EXAMPLE 2: Batch Action Processing")
    print("="*50)
    
    # Define multiple actions
    actions = [
        "GOTO URL : https://example.com",
        "GO TO URL : https://www.w3.org",
        "VISIT : https://httpbin.org/html"
    ]
    
    # Process all actions
    results = process_actions_from_list(actions)
    
    # Show results summary
    successful = [r for r in results if r.get("success", False)]
    failed = [r for r in results if not r.get("success", False)]
    
    print(f"📊 Batch Results:")
    print(f"   Total: {len(results)}")
    print(f"   Successful: {len(successful)}")
    print(f"   Failed: {len(failed)}")
    
    for result in successful:
        print(f"   ✅ {result['url']} -> {sum(result['selectors_count'].values())} selectors")
    
    for result in failed:
        print(f"   ❌ {result.get('url', 'unknown')} -> {result.get('error', 'unknown error')}")


def example_accessing_extracted_data():
    """
    Example of accessing and working with extracted selector data.
    """
    print(f"\n🔥 EXAMPLE 3: Accessing Extracted Data")
    print("="*50)
    
    # Initialize handler to access the mapping
    handler = ActionHandler()
    
    # Get the latest successful action
    history = handler.get_action_history()
    successful_actions = [a for a in history if a.get("status") == "completed"]
    
    if not successful_actions:
        print("❌ No successful actions found. Run examples 1 or 2 first.")
        return
    
    # Get the most recent successful action
    latest_action = successful_actions[-1]
    
    print(f"🔍 Latest successful action:")
    print(f"   Action: {latest_action['action_string']}")
    print(f"   URL: {latest_action['url']}")
    print(f"   File: {latest_action['selector_file_path']}")
    
    # Load and display the selector data
    selector_file = latest_action['absolute_selector_file_path']
    try:
        with open(selector_file, 'r', encoding='utf-8') as f:
            selectors = json.load(f)
        
        print(f"\n📄 Selector File Content Preview:")
        print(f"   Total Elements: {selectors['statistics']['total_elements']}")
        print(f"   Unique Tags: {len(selectors['statistics']['unique_tags'])}")
        
        # Show some ID selectors if available
        if selectors.get('id_selectors'):
            print(f"\n🆔 Sample ID Selectors:")
            for selector in selectors['id_selectors'][:3]:
                print(f"   - {selector['selector']} ({selector['tag']})")
        
        # Show some class selectors if available
        if selectors.get('class_selectors'):
            print(f"\n🎨 Sample Class Selectors:")
            for selector in selectors['class_selectors'][:3]:
                print(f"   - {selector['selector']} ({selector['tag']})")
        
        # Show input selectors if available
        if selectors.get('input_selectors'):
            print(f"\n📝 Input Selectors:")
            for input_sel in selectors['input_selectors'][:2]:
                print(f"   - Type: {input_sel['type']}, Selectors: {input_sel['selectors'][:2]}")
        
        # Show combined patterns if available
        if selectors.get('combined_selectors'):
            print(f"\n🎯 Combined Patterns:")
            for pattern in selectors['combined_selectors'][:3]:
                print(f"   - {pattern['pattern']} ({pattern['description']}) - {pattern['count']} matches")
    
    except Exception as e:
        print(f"❌ Error reading selector file: {e}")


def example_custom_processing():
    """
    Example of custom processing and filtering of selectors.
    """
    print(f"\n🔥 EXAMPLE 4: Custom Selector Processing")
    print("="*50)
    
    # Process a URL with many form elements
    handler = ActionHandler()
    
    # For this example, let's create some sample selector data
    # In real usage, this would come from processing an actual URL
    sample_selectors = {
        "id_selectors": [
            {"selector": "#login-form", "tag": "form"},
            {"selector": "#username", "tag": "input"},
            {"selector": "#password", "tag": "input"},
            {"selector": "#submit-btn", "tag": "button"}
        ],
        "class_selectors": [
            {"selector": ".form-control", "tag": "input"},
            {"selector": ".btn-primary", "tag": "button"},
            {"selector": ".nav-link", "tag": "a"}
        ],
        "input_selectors": [
            {
                "type": "text",
                "name": "username",
                "selectors": ["#username", "input[name='username']", "input[type='text']"]
            },
            {
                "type": "password", 
                "name": "password",
                "selectors": ["#password", "input[name='password']", "input[type='password']"]
            }
        ]
    }
    
    # Custom processing: Extract login-related selectors
    login_selectors = []
    
    # Find form-related ID selectors
    for selector in sample_selectors.get("id_selectors", []):
        if any(keyword in selector["selector"].lower() for keyword in ["login", "form", "username", "password", "submit"]):
            login_selectors.append(selector["selector"])
    
    # Find input selectors for login
    for input_sel in sample_selectors.get("input_selectors", []):
        if input_sel["type"] in ["text", "email", "password"]:
            login_selectors.extend(input_sel["selectors"])
    
    print(f"🔐 Extracted Login-Related Selectors:")
    for selector in set(login_selectors):  # Remove duplicates
        print(f"   - {selector}")
    
    print(f"\n💡 This shows how you can filter and process selectors")
    print(f"   for specific use cases like login automation!")


def main():
    """
    Run all examples.
    """
    print("🚀 ACTION HANDLER SYSTEM - USAGE EXAMPLES")
    print("="*60)
    
    # Run all examples
    example_single_action()
    example_batch_processing()
    example_accessing_extracted_data()
    example_custom_processing()
    
    print(f"\n🎉 All examples completed!")
    print(f"\nNext steps:")
    print(f"- Check ../extracted_data/ for generated files")
    print(f"- Use action_handler.py for single actions")
    print(f"- Use batch_action_processor.py for multiple actions")
    print(f"- Customize selector filtering for your needs")


if __name__ == "__main__":
    main()