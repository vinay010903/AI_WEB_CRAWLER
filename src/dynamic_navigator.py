import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from ai_page_analyzer import AIPageAnalyzer, PageType, PageAnalysis

@dataclass
class NavigationAction:
    action_type: str  # click, fill, select, hover, scroll, wait
    selector: str
    value: Optional[str] = None
    wait_after: int = 2
    success_indicator: Optional[str] = None
    failure_indicator: Optional[str] = None

@dataclass
class NavigationGoal:
    goal_name: str
    description: str
    success_criteria: List[str]
    max_steps: int = 10
    timeout: int = 60

class DynamicNavigator:
    """AI-powered dynamic website navigation system"""
    
    def __init__(self, model_name: str = "openai/gpt-oss-20b"):
        self.ai_analyzer = AIPageAnalyzer(model_name)
        self.navigation_history = []
        self.failed_attempts = []
        
    async def navigate_to_goal(self, page: Page, goal: NavigationGoal, context: Dict = None) -> Dict[str, Any]:
        """Navigate through website to achieve a specific goal"""
        
        print(f"🎯 Starting navigation to achieve: {goal.goal_name}")
        
        steps_taken = 0
        start_time = asyncio.get_event_loop().time()
        
        while steps_taken < goal.max_steps:
            current_time = asyncio.get_event_loop().time()
            if current_time - start_time > goal.timeout:
                return {"success": False, "error": "Navigation timeout", "steps_taken": steps_taken}
            
            # Analyze current page
            html_content = await page.content()
            current_url = page.url
            
            page_analysis = await self.ai_analyzer.analyze_page_structure(html_content, current_url)
            print(f"📄 Current page: {page_analysis.page_type.value}")
            
            # Check if we've achieved the goal
            if await self._check_goal_completion(page, goal, page_analysis):
                return {
                    "success": True, 
                    "steps_taken": steps_taken,
                    "final_url": current_url,
                    "page_type": page_analysis.page_type.value
                }
            
            # Generate next action using AI
            next_action = await self._generate_next_action(page_analysis, goal, context, html_content)
            
            if not next_action:
                return {"success": False, "error": "No valid action found", "steps_taken": steps_taken}
            
            # Execute the action
            action_result = await self._execute_action(page, next_action)
            
            if not action_result["success"]:
                print(f"❌ Action failed: {action_result['error']}")
                self.failed_attempts.append({
                    "step": steps_taken,
                    "action": next_action,
                    "error": action_result["error"],
                    "url": current_url
                })
                
                # Try to recover or find alternative
                recovery_result = await self._attempt_recovery(page, goal, page_analysis)
                if not recovery_result["success"]:
                    return {"success": False, "error": "Recovery failed", "steps_taken": steps_taken}
            
            self.navigation_history.append({
                "step": steps_taken,
                "action": next_action,
                "result": action_result,
                "url": current_url
            })
            
            steps_taken += 1
            await asyncio.sleep(2)  # Allow page to settle
        
        return {"success": False, "error": "Max steps exceeded", "steps_taken": steps_taken}

    async def smart_search(self, page: Page, search_term: str, search_context: str = "") -> Dict[str, Any]:
        """Intelligently find and use search functionality"""
        
        print(f"🔍 Smart search for: {search_term}")
        
        html_content = await page.content()
        page_analysis = await self.ai_analyzer.analyze_page_structure(html_content, page.url)
        
        # Extract selectors
        from test_extract_selector import extract_all_selectors
        from utilities_local_ai import local_ai_selector_categorizer
        from main import group_selectors_by_category
        
        simple_selectors = extract_all_selectors(html_content, None)
        categorized_selectors = local_ai_selector_categorizer(simple_selectors, "qwen/qwen3-4b-2507")
        grouped_selectors = group_selectors_by_category(simple_selectors, categorized_selectors)
        
        # Find search elements
        search_selector = await self._find_search_input(grouped_selectors, search_context)
        
        if not search_selector:
            return {"success": False, "error": "No search input found"}
        
        try:
            # Fill search term
            await page.fill(search_selector, search_term)
            print(f"✅ Search term filled: {search_selector}")
            
            # Try to submit search
            search_result = await self._submit_search(page, grouped_selectors)
            
            if search_result["success"]:
                await self._wait_for_search_results(page)
                return {"success": True, "search_selector": search_selector, "method": search_result["method"]}
            else:
                return {"success": False, "error": "Search submission failed"}
                
        except Exception as e:
            return {"success": False, "error": f"Search execution failed: {str(e)}"}

    async def smart_product_interaction(self, page: Page, interaction_type: str, product_context: str = "") -> Dict[str, Any]:
        """Handle product-related interactions (view details, add to cart, etc.)"""
        
        print(f"🛍️ Product interaction: {interaction_type}")
        
        html_content = await page.content()
        
        # Extract selectors
        from test_extract_selector import extract_all_selectors
        from utilities_local_ai import local_ai_selector_categorizer
        from main import group_selectors_by_category
        
        simple_selectors = extract_all_selectors(html_content, None)
        categorized_selectors = local_ai_selector_categorizer(simple_selectors, "qwen/qwen3-4b-2507")
        grouped_selectors = group_selectors_by_category(simple_selectors, categorized_selectors)
        
        # Find appropriate selector based on interaction type
        selector = await self._find_product_interaction_selector(grouped_selectors, interaction_type, product_context)
        
        if not selector:
            return {"success": False, "error": f"No selector found for {interaction_type}"}
        
        try:
            await page.click(selector)
            print(f"✅ {interaction_type} completed: {selector}")
            
            await asyncio.sleep(3)  # Allow page to respond
            
            return {"success": True, "selector": selector, "interaction": interaction_type}
            
        except Exception as e:
            return {"success": False, "error": f"{interaction_type} failed: {str(e)}"}

    async def handle_dynamic_forms(self, page: Page, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle dynamic form filling using AI to identify fields"""
        
        print("📋 Handling dynamic form")
        
        html_content = await page.content()
        
        # Extract selectors
        from test_extract_selector import extract_all_selectors
        from utilities_local_ai import local_ai_selector_categorizer
        from main import group_selectors_by_category
        
        simple_selectors = extract_all_selectors(html_content, None)
        categorized_selectors = local_ai_selector_categorizer(simple_selectors, "qwen/qwen3-4b-2507")
        grouped_selectors = group_selectors_by_category(simple_selectors, categorized_selectors)
        
        filled_fields = []
        failed_fields = []
        
        for field_name, field_value in form_data.items():
            print(f"📝 Filling field: {field_name}")
            
            # Find selector for this field
            field_selector = await self._find_form_field_selector(grouped_selectors, field_name, str(field_value))
            
            if field_selector:
                try:
                    # Determine input type and fill accordingly
                    element = await page.query_selector(field_selector)
                    if element:
                        tag_name = await element.get_attribute("tagName")
                        input_type = await element.get_attribute("type")
                        
                        if tag_name.lower() == "select":
                            await page.select_option(field_selector, str(field_value))
                        elif input_type in ["checkbox", "radio"]:
                            if field_value:
                                await page.check(field_selector)
                        else:
                            await page.fill(field_selector, str(field_value))
                        
                        filled_fields.append({"field": field_name, "selector": field_selector})
                        print(f"✅ Field filled: {field_name}")
                    
                except Exception as e:
                    failed_fields.append({"field": field_name, "error": str(e)})
                    print(f"❌ Failed to fill {field_name}: {e}")
            else:
                failed_fields.append({"field": field_name, "error": "Selector not found"})
                print(f"❌ No selector found for field: {field_name}")
        
        # Try to submit form
        submit_result = await self._submit_form(page, grouped_selectors)
        
        return {
            "success": len(failed_fields) == 0,
            "filled_fields": filled_fields,
            "failed_fields": failed_fields,
            "submit_result": submit_result
        }

    async def _check_goal_completion(self, page: Page, goal: NavigationGoal, page_analysis: PageAnalysis) -> bool:
        """Check if navigation goal has been achieved"""
        
        current_url = page.url
        page_type = page_analysis.page_type.value
        
        for criterion in goal.success_criteria:
            if criterion.startswith("url_contains:"):
                expected_url_part = criterion.split(":", 1)[1]
                if expected_url_part not in current_url:
                    return False
            
            elif criterion.startswith("page_type:"):
                expected_page_type = criterion.split(":", 1)[1]
                if page_type != expected_page_type:
                    return False
            
            elif criterion.startswith("element_exists:"):
                selector = criterion.split(":", 1)[1]
                element = await page.query_selector(selector)
                if not element:
                    return False
            
            elif criterion.startswith("text_visible:"):
                expected_text = criterion.split(":", 1)[1]
                try:
                    await page.wait_for_selector(f"text={expected_text}", timeout=5000)
                except:
                    return False
        
        return True

    async def _generate_next_action(self, page_analysis: PageAnalysis, goal: NavigationGoal, context: Dict, html_content: str) -> Optional[NavigationAction]:
        """Generate next action using AI"""
        
        strategy = await self.ai_analyzer.generate_navigation_strategy(page_analysis, goal.description)
        
        if not strategy or not strategy.get("steps"):
            return None
        
        # Get first unexecuted step
        current_step = len(self.navigation_history)
        if current_step < len(strategy["steps"]):
            step = strategy["steps"][current_step]
            
            return NavigationAction(
                action_type=step.get("action", "click"),
                selector=step.get("target", ""),
                value=step.get("value"),
                wait_after=step.get("timeout", 2),
                success_indicator=None,
                failure_indicator=None
            )
        
        return None

    async def _execute_action(self, page: Page, action: NavigationAction) -> Dict[str, Any]:
        """Execute a navigation action"""
        
        try:
            if action.action_type == "click":
                await page.click(action.selector)
                
            elif action.action_type == "fill_input":
                if action.value:
                    await page.fill(action.selector, action.value)
                
            elif action.action_type == "select":
                if action.value:
                    await page.select_option(action.selector, action.value)
                
            elif action.action_type == "hover":
                await page.hover(action.selector)
                
            elif action.action_type == "wait":
                await asyncio.sleep(int(action.value or 3))
                
            elif action.action_type == "scroll":
                await page.evaluate(f"document.querySelector('{action.selector}').scrollIntoView()")
            
            # Wait for action to complete
            await asyncio.sleep(action.wait_after)
            
            return {"success": True, "action": action.action_type}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _attempt_recovery(self, page: Page, goal: NavigationGoal, page_analysis: PageAnalysis) -> Dict[str, Any]:
        """Attempt to recover from failed action"""
        
        # Analyze current state and suggest fixes
        html_content = await page.content()
        
        error_analysis = await self.ai_analyzer.analyze_errors_and_suggest_fixes(
            f"Navigation failed while trying to achieve: {goal.description}",
            html_content
        )
        
        if error_analysis.get("suggested_fixes"):
            for fix in error_analysis["suggested_fixes"][:2]:  # Try top 2 fixes
                if fix.get("fix_type") == "retry":
                    await asyncio.sleep(3)
                    return {"success": True, "recovery": "retry"}
                    
                elif fix.get("fix_type") == "wait":
                    await asyncio.sleep(5)
                    return {"success": True, "recovery": "wait"}
        
        return {"success": False, "error": "No recovery options available"}

    async def _find_search_input(self, grouped_selectors: Dict, context: str = "") -> Optional[str]:
        """Find search input field"""
        
        search_categories = ["search_filters", "input_form", "navigation"]
        all_selectors = []
        
        for category in search_categories:
            if category in grouped_selectors:
                all_selectors.extend(grouped_selectors[category])
        
        if not all_selectors:
            return None
        
        result = await self.ai_analyzer.find_best_selector(
            all_selectors, 
            "fill_search", 
            f"Find search input box. Context: {context}"
        )
        
        return result.get("best_selector")

    async def _submit_search(self, page: Page, grouped_selectors: Dict) -> Dict[str, Any]:
        """Submit search using various methods"""
        
        # Method 1: Try Enter key
        try:
            await page.keyboard.press("Enter")
            await asyncio.sleep(2)
            return {"success": True, "method": "enter_key"}
        except:
            pass
        
        # Method 2: Find and click search button
        all_selectors = []
        for category, selectors in grouped_selectors.items():
            all_selectors.extend(selectors)
        
        search_button = await self.ai_analyzer.find_best_selector(
            all_selectors,
            "click_search_button",
            "Find search button or submit button"
        )
        
        if search_button:
            try:
                await page.click(search_button.get("best_selector"))
                return {"success": True, "method": "search_button"}
            except:
                pass
        
        # Method 3: Submit form
        try:
            await page.evaluate("document.querySelector('form').submit()")
            return {"success": True, "method": "form_submit"}
        except:
            pass
        
        return {"success": False, "method": "none"}

    async def _wait_for_search_results(self, page: Page):
        """Wait for search results to load"""
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            await asyncio.sleep(2)
        except:
            pass

    async def _find_product_interaction_selector(self, grouped_selectors: Dict, interaction_type: str, context: str) -> Optional[str]:
        """Find selector for product interaction"""
        
        product_categories = ["product_items", "ecommerce", "buttons", "links"]
        all_selectors = []
        
        for category in product_categories:
            if category in grouped_selectors:
                all_selectors.extend(grouped_selectors[category])
        
        if not all_selectors:
            return None
        
        task_mapping = {
            "view_product": "click_product_link",
            "add_to_cart": "click_add_to_cart",
            "view_details": "click_product_details",
            "quick_view": "click_quick_view",
            "compare": "click_compare",
            "wishlist": "click_wishlist"
        }
        
        task = task_mapping.get(interaction_type, f"click_{interaction_type}")
        
        result = await self.ai_analyzer.find_best_selector(
            all_selectors,
            task,
            f"Find {interaction_type} button/link. Context: {context}"
        )
        
        return result.get("best_selector")

    async def _find_form_field_selector(self, grouped_selectors: Dict, field_name: str, field_value: str) -> Optional[str]:
        """Find selector for form field"""
        
        form_categories = ["input_form", "authentication_account", "input_selectors"]
        all_selectors = []
        
        for category in form_categories:
            if category in grouped_selectors:
                all_selectors.extend(grouped_selectors[category])
        
        if not all_selectors:
            return None
        
        result = await self.ai_analyzer.find_best_selector(
            all_selectors,
            f"fill_{field_name}",
            f"Find input field for {field_name}. Value will be: {field_value}"
        )
        
        return result.get("best_selector")

    async def _submit_form(self, page: Page, grouped_selectors: Dict) -> Dict[str, Any]:
        """Submit form"""
        
        all_selectors = []
        for category, selectors in grouped_selectors.items():
            all_selectors.extend(selectors)
        
        submit_selector = await self.ai_analyzer.find_best_selector(
            all_selectors,
            "click_submit",
            "Find form submit button"
        )
        
        if submit_selector and submit_selector.get("best_selector"):
            try:
                await page.click(submit_selector["best_selector"])
                await asyncio.sleep(3)
                return {"success": True, "selector": submit_selector["best_selector"]}
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "Submit button not found"}