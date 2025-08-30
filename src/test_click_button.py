#!/usr/bin/env python3
"""
Test script for CLICK BUTTON functionality in ActionHandler.

This script creates a test HTML page and tests various button clicking scenarios.
"""

import asyncio
import os
import tempfile
from action_handler import ActionHandler

# Sample HTML with various button types for testing
TEST_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Button Click Test Page</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        .button { margin: 10px; padding: 10px; }
        .hidden { display: none; }
        .success { color: green; font-weight: bold; }
    </style>
</head>
<body>
    <h1>Button Click Test Page</h1>
    
    <div class="button-section">
        <h2>Standard Buttons</h2>
        <button id="submit-btn" onclick="showSuccess('Submit button clicked!')">Submit</button>
        <button class="search-button" onclick="showSuccess('Search button clicked!')">Search</button>
        <button name="login-btn" onclick="showSuccess('Login button clicked!')">Login</button>
        
        <h2>Input Buttons</h2>
        <input type="button" id="input-btn" value="Input Button" onclick="showSuccess('Input button clicked!')">
        <input type="submit" value="Submit Input" onclick="showSuccess('Submit input clicked!')">
        
        <h2>Text-based Selection</h2>
        <button onclick="showSuccess('Save clicked!')">Save</button>
        <button onclick="showSuccess('Cancel clicked!')">Cancel</button>
        <button onclick="showSuccess('Continue clicked!')">Continue</button>
        
        <h2>Attribute-based</h2>
        <button data-testid="test-button" onclick="showSuccess('Test button clicked!')">Test Button</button>
        <button data-hook="action-button" onclick="showSuccess('Action button clicked!')">Action Button</button>
        <button aria-label="Close dialog" onclick="showSuccess('Close button clicked!')">×</button>
        
        <h2>Form Buttons</h2>
        <form>
            <button type="button" onclick="showSuccess('Form button clicked!')">Form Button</button>
            <button type="submit" onclick="event.preventDefault(); showSuccess('Form submit clicked!')">Form Submit</button>
        </form>
    </div>
    
    <div id="success-message" class="success hidden"></div>
    
    <script>
        function showSuccess(message) {
            const msgDiv = document.getElementById('success-message');
            msgDiv.textContent = message;
            msgDiv.classList.remove('hidden');
            setTimeout(() => {
                msgDiv.classList.add('hidden');
            }, 3000);
        }
    </script>
</body>
</html>
"""

async def create_test_file():
    """
    Create a temporary HTML file for testing.
    
    Returns:
        str: Path to the test HTML file
    """
    # Create a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8') as f:
        f.write(TEST_HTML)
        temp_file_path = f.name
    
    # Convert to file:// URL
    file_url = f"file://{os.path.abspath(temp_file_path)}"
    print(f"📄 Created test HTML file: {file_url}")
    return file_url, temp_file_path

async def test_click_scenarios():
    """
    Test various CLICK BUTTON scenarios.
    """
    print("🧪 Starting CLICK BUTTON functionality tests...")
    
    # Create test HTML file
    test_url, temp_file_path = await create_test_file()
    
    # Initialize action handler in non-headless mode to see results
    handler = ActionHandler(headless=False)
    
    try:
        # First, navigate to the test page
        print("\n🌐 Step 1: Navigate to test page")
        goto_result = await handler.process_action(f"GOTO URL : {test_url}")
        
        if not goto_result["success"]:
            print(f"❌ Failed to navigate: {goto_result['error']}")
            return
        
        print("✅ Successfully navigated to test page")
        
        # Wait a moment for page to load
        await asyncio.sleep(3)
        
        # Test scenarios
        test_scenarios = [
            # ID selector
            ("CLICK BUTTON #submit-btn", "Testing ID selector"),
            
            # Class selector
            ("CLICK BUTTON .search-button", "Testing class selector"),
            
            # Name attribute
            ("CLICK BUTTON login-btn", "Testing name attribute"),
            
            # Text-based selection
            ("CLICK BUTTON Save", "Testing text-based selection"),
            
            # Input button by ID
            ("CLICK BUTTON #input-btn", "Testing input button by ID"),
            
            # Input button by value
            ("CLICK BUTTON Submit Input", "Testing input button by value text"),
            
            # Data attribute selectors
            ("CLICK BUTTON test-button", "Testing data-testid"),
            
            # Aria label
            ("CLICK BUTTON Close dialog", "Testing aria-label"),
            
            # Form button
            ("CLICK BUTTON Form Button", "Testing form button"),
        ]
        
        print(f"\n🎯 Running {len(test_scenarios)} click tests...")
        successful_tests = 0
        
        for i, (action, description) in enumerate(test_scenarios, 1):
            print(f"\n--- Test {i}/{len(test_scenarios)}: {description} ---")
            print(f"Action: {action}")
            
            # Perform the click action
            result = await handler.process_action(action)
            
            if result["success"]:
                print(f"✅ SUCCESS: {result.get('selector_used', 'N/A')}")
                successful_tests += 1
                
                # Wait to see the result
                await asyncio.sleep(2)
            else:
                print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
                if 'selectors_tried' in result:
                    print(f"   Selectors tried: {len(result['selectors_tried'])}")
        
        # Test summary
        print(f"\n📊 TEST SUMMARY:")
        print(f"   Total tests: {len(test_scenarios)}")
        print(f"   Successful: {successful_tests}")
        print(f"   Failed: {len(test_scenarios) - successful_tests}")
        print(f"   Success rate: {successful_tests/len(test_scenarios)*100:.1f}%")
        
        # Show action history
        print(f"\n📚 Recent actions:")
        history = handler.get_action_history()
        click_actions = [a for a in history if a.get("action_type") == "click_button"][-5:]
        for action in click_actions:
            status = "✅" if action.get("status") == "completed" else "❌"
            print(f"   {status} {action.get('action_string', 'N/A')}")
        
        # Keep browser open for a few seconds to see final state
        print(f"\n⏳ Keeping browser open for 5 seconds to see results...")
        await asyncio.sleep(5)
        
    except Exception as e:
        print(f"❌ Test error: {e}")
    
    finally:
        # Clean up
        await handler.close_browser()
        
        # Remove temporary file
        try:
            os.unlink(temp_file_path)
            print(f"🗑️  Cleaned up temporary file")
        except:
            pass

async def test_error_scenarios():
    """
    Test error scenarios for CLICK BUTTON functionality.
    """
    print("\n🧪 Testing error scenarios...")
    
    handler = ActionHandler(headless=True)
    
    try:
        # Test 1: Click button without navigating first
        print("\n--- Error Test 1: Click without navigation ---")
        result = await handler.process_action("CLICK BUTTON Submit")
        if not result["success"]:
            print(f"✅ Expected error: {result['error']}")
        else:
            print(f"❌ Unexpected success")
        
        # Test 2: Navigate to page and try non-existent button
        test_url, temp_file_path = await create_test_file()
        goto_result = await handler.process_action(f"GOTO URL : {test_url}")
        
        if goto_result["success"]:
            print("\n--- Error Test 2: Non-existent button ---")
            result = await handler.process_action("CLICK BUTTON NonExistentButton")
            if not result["success"]:
                print(f"✅ Expected error: {result['error']}")
            else:
                print(f"❌ Unexpected success")
        
        # Test 3: Invalid action format
        print("\n--- Error Test 3: Invalid action format ---")
        result = await handler.process_action("INVALID ACTION FORMAT")
        if not result["success"]:
            print(f"✅ Expected error: {result['error']}")
        else:
            print(f"❌ Unexpected success")
    
    finally:
        await handler.close_browser()
        try:
            os.unlink(temp_file_path)
        except:
            pass

async def main():
    """
    Run all tests.
    """
    print("🚀 CLICK BUTTON FUNCTIONALITY TESTS")
    print("="*50)
    
    # Run main functionality tests
    await test_click_scenarios()
    
    # Run error scenario tests
    await test_error_scenarios()
    
    print(f"\n🎉 All tests completed!")

if __name__ == "__main__":
    asyncio.run(main())