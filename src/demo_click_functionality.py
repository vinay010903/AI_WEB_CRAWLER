#!/usr/bin/env python3
"""
Demo script showing CLICK BUTTON functionality in ActionHandler.

This script demonstrates how to use the action handler with both
GOTO URL and CLICK BUTTON actions in sequence.
"""

import asyncio
from action_handler import ActionHandler

async def demo_click_functionality():
    """
    Demonstrate CLICK BUTTON functionality with a real website.
    """
    print("🎭 CLICK BUTTON FUNCTIONALITY DEMO")
    print("="*50)
    
    # Initialize action handler (non-headless to see what happens)
    handler = ActionHandler(headless=False)
    
    try:
        # Step 1: Navigate to a page with buttons
        print("\n🌐 Step 1: Navigate to httpbin.org/forms/post")
        result = await handler.process_action("GOTO URL : https://httpbin.org/forms/post")
        
        if not result["success"]:
            print(f"❌ Navigation failed: {result['error']}")
            return
        
        print("✅ Successfully navigated!")
        await asyncio.sleep(3)  # Wait for page to load
        
        # Step 2: Try to fill some form data and click submit
        print("\n🔘 Step 2: Attempting to click Submit button")
        click_result = await handler.process_action("CLICK BUTTON Submit")
        
        if click_result["success"]:
            print(f"✅ Button clicked successfully!")
            print(f"   Selector used: {click_result.get('selector_used')}")
            print(f"   Current URL: {click_result.get('current_url')}")
        else:
            print(f"❌ Click failed: {click_result.get('error')}")
        
        # Step 3: Wait to see the result
        print("\n⏳ Waiting 5 seconds to observe the result...")
        await asyncio.sleep(5)
        
        # Step 4: Show action summary
        print(f"\n📊 Action Summary:")
        history = handler.get_action_history()
        recent_actions = history[-2:]  # Show last 2 actions
        
        for i, action in enumerate(recent_actions, 1):
            action_type = action.get('action_type', 'goto_url')
            status = "✅" if action.get("status") == "completed" else "❌"
            print(f"{i}. {status} {action_type.upper()}: {action.get('action_string')}")
            
            if action_type == 'click_button' and action.get('click_result'):
                selector = action['click_result'].get('selector_used', 'N/A')
                print(f"   → Used selector: {selector}")
    
    except Exception as e:
        print(f"❌ Demo error: {e}")
    
    finally:
        await handler.close_browser()

def demo_parsing_functionality():
    """
    Demonstrate the action parsing functionality.
    """
    print(f"\n🧠 DEMO: Action Parsing Functionality")
    print("="*40)
    
    handler = ActionHandler()
    
    test_actions = [
        "GOTO URL : https://example.com",
        "CLICK BUTTON Submit",
        "CLICK BUTTON #login-btn",
        "CLICK .search-button",
        "PRESS BUTTON Continue",
        "TAP Save",
        "https://www.google.com",
        "INVALID ACTION"
    ]
    
    for action in test_actions:
        action_type = handler.parse_action_type(action)
        print(f"Action: '{action}'")
        print(f"   → Type: {action_type}")
        
        if action_type == 'goto_url':
            url = handler.parse_goto_action(action)
            print(f"   → Parsed URL: {url}")
        elif action_type == 'click_button':
            button = handler.parse_click_button_action(action)
            print(f"   → Parsed Button: {button}")
        
        print()

def demo_synchronous_usage():
    """
    Show how to use the action handler from synchronous code.
    """
    print(f"\n🔄 DEMO: Synchronous Usage Examples")
    print("="*40)
    
    print("Example command line usage:")
    print('  python action_handler.py "GOTO URL : https://example.com"')
    print('  python action_handler.py "CLICK BUTTON Submit"')
    print('  python action_handler.py "CLICK BUTTON #login-btn"')
    print('  python action_handler.py "CLICK .search-button"')
    
    print(f"\nExample programmatic usage:")
    print("""
import asyncio
from action_handler import ActionHandler

async def my_automation():
    handler = ActionHandler(headless=False)
    try:
        # Navigate to page
        await handler.process_action("GOTO URL : https://example.com")
        
        # Click a button
        await handler.process_action("CLICK BUTTON Submit")
        
    finally:
        await handler.close_browser()

# Run the automation
asyncio.run(my_automation())
    """)

async def main():
    """
    Run all demos.
    """
    # Demo 1: Action parsing
    demo_parsing_functionality()
    
    # Demo 2: Synchronous usage examples
    demo_synchronous_usage()
    
    # Demo 3: Live click functionality (commented out by default)
    # Uncomment the line below to run the live demo
    # await demo_click_functionality()
    
    print(f"\n🎉 Demo completed!")
    print(f"\nNext steps:")
    print(f"1. Run: python test_click_button.py (for comprehensive testing)")
    print(f"2. Try: python action_handler.py \"GOTO URL : https://httpbin.org/forms/post\"")
    print(f"3. Then: python action_handler.py \"CLICK BUTTON Submit\"")

if __name__ == "__main__":
    asyncio.run(main())