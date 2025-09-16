import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from ai_page_analyzer import AIPageAnalyzer

class ErrorType(Enum):
    TIMEOUT = "timeout"
    SELECTOR_NOT_FOUND = "selector_not_found"
    ELEMENT_NOT_CLICKABLE = "element_not_clickable"
    NAVIGATION_FAILED = "navigation_failed"
    FORM_SUBMISSION_FAILED = "form_submission_failed"
    CAPTCHA_REQUIRED = "captcha_required"
    RATE_LIMITED = "rate_limited"
    AUTHENTICATION_FAILED = "authentication_failed"
    NETWORK_ERROR = "network_error"
    PAGE_LOAD_ERROR = "page_load_error"
    JAVASCRIPT_ERROR = "javascript_error"
    ACCESS_DENIED = "access_denied"
    UNKNOWN = "unknown"

@dataclass
class ErrorContext:
    error_type: ErrorType
    error_message: str
    current_url: str
    target_selector: Optional[str] = None
    action_attempted: Optional[str] = None
    page_content: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    retry_count: int = 0
    max_retries: int = 3

@dataclass
class RecoveryStrategy:
    strategy_name: str
    steps: List[Dict[str, Any]]
    success_probability: float
    estimated_time: int
    prerequisites: List[str] = field(default_factory=list)

class ErrorRecoverySystem:
    """AI-powered error recovery and retry system"""
    
    def __init__(self, model_name: str = "openai/gpt-oss-20b"):
        self.ai_analyzer = AIPageAnalyzer(model_name)
        self.error_history = []
        self.recovery_stats = {
            "total_errors": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "recovery_methods": {}
        }
        
    async def handle_error(self, page: Page, error_context: ErrorContext, custom_strategies: List[RecoveryStrategy] = None) -> Dict[str, Any]:
        """Main error handling method"""
        
        print(f"🚨 Error detected: {error_context.error_type.value}")
        print(f"🔍 Error message: {error_context.error_message}")
        
        self.error_history.append(error_context)
        self.recovery_stats["total_errors"] += 1
        
        # Check if we've exceeded max retries
        if error_context.retry_count >= error_context.max_retries:
            return {
                "success": False,
                "error": "Max retries exceeded",
                "retry_count": error_context.retry_count
            }
        
        # Analyze error and generate recovery strategies
        recovery_strategies = await self._generate_recovery_strategies(page, error_context)
        
        # Add custom strategies if provided
        if custom_strategies:
            recovery_strategies.extend(custom_strategies)
        
        # Sort by success probability
        recovery_strategies.sort(key=lambda x: x.success_probability, reverse=True)
        
        # Attempt recovery strategies
        for strategy in recovery_strategies[:3]:  # Try top 3 strategies
            print(f"🔧 Attempting recovery strategy: {strategy.strategy_name}")
            
            recovery_result = await self._execute_recovery_strategy(page, strategy, error_context)
            
            if recovery_result.get("success"):
                print(f"✅ Recovery successful using: {strategy.strategy_name}")
                self.recovery_stats["successful_recoveries"] += 1
                self._update_recovery_stats(strategy.strategy_name, True)
                
                return {
                    "success": True,
                    "recovery_method": strategy.strategy_name,
                    "retry_count": error_context.retry_count + 1
                }
            else:
                print(f"❌ Recovery strategy failed: {recovery_result.get('error')}")
                self._update_recovery_stats(strategy.strategy_name, False)
        
        self.recovery_stats["failed_recoveries"] += 1
        return {
            "success": False,
            "error": "All recovery strategies failed",
            "strategies_attempted": [s.strategy_name for s in recovery_strategies[:3]],
            "retry_count": error_context.retry_count
        }

    async def _generate_recovery_strategies(self, page: Page, error_context: ErrorContext) -> List[RecoveryStrategy]:
        """Generate recovery strategies using AI"""
        
        # Get current page content for analysis
        try:
            current_content = await page.content()
            current_url = page.url
        except:
            current_content = error_context.page_content or ""
            current_url = error_context.current_url
        
        strategy_prompt = f"""
        Analyze this error and generate recovery strategies:
        
        Error Type: {error_context.error_type.value}
        Error Message: {error_context.error_message}
        Current URL: {current_url}
        Target Selector: {error_context.target_selector}
        Action Attempted: {error_context.action_attempted}
        Retry Count: {error_context.retry_count}
        
        Current page content (first 5000 chars): {current_content[:5000]}
        
        Generate recovery strategies based on error type:
        
        For TIMEOUT errors:
        - Increase wait time
        - Wait for specific elements
        - Reload page
        - Check network connectivity
        
        For SELECTOR_NOT_FOUND errors:
        - Try alternative selectors
        - Wait for dynamic content
        - Refresh page
        - Check for page structure changes
        
        For ELEMENT_NOT_CLICKABLE errors:
        - Scroll element into view
        - Remove overlays
        - Wait for animations
        - Try different click methods
        
        For CAPTCHA_REQUIRED errors:
        - Solve CAPTCHA
        - Wait and retry
        - Use different approach
        
        For RATE_LIMITED errors:
        - Implement exponential backoff
        - Change user agent
        - Add delays
        - Use proxy rotation
        
        Return JSON with recovery strategies:
        {{
            "strategies": [
                {{
                    "strategy_name": "descriptive_name",
                    "steps": [
                        {{
                            "action": "wait/reload/scroll/click/etc",
                            "target": "selector_or_description",
                            "parameters": {{"timeout": 10, "method": "specific"}},
                            "expected_result": "what_should_happen"
                        }}
                    ],
                    "success_probability": 0.8,
                    "estimated_time": 15,
                    "prerequisites": ["conditions_needed"],
                    "description": "what_this_strategy_does"
                }}
            ]
        }}
        """
        
        try:
            result = await self.ai_analyzer._query_ai(strategy_prompt)
            strategies_data = result.get("strategies", [])
            
            recovery_strategies = []
            for strategy_data in strategies_data:
                strategy = RecoveryStrategy(
                    strategy_name=strategy_data.get("strategy_name", "unnamed"),
                    steps=strategy_data.get("steps", []),
                    success_probability=strategy_data.get("success_probability", 0.5),
                    estimated_time=strategy_data.get("estimated_time", 10),
                    prerequisites=strategy_data.get("prerequisites", [])
                )
                recovery_strategies.append(strategy)
            
            return recovery_strategies
            
        except Exception as e:
            print(f"⚠️ Failed to generate AI strategies: {e}")
            return await self._get_default_recovery_strategies(error_context)

    async def _get_default_recovery_strategies(self, error_context: ErrorContext) -> List[RecoveryStrategy]:
        """Get default recovery strategies based on error type"""
        
        default_strategies = {
            ErrorType.TIMEOUT: [
                RecoveryStrategy(
                    strategy_name="increase_timeout_and_retry",
                    steps=[
                        {"action": "wait", "target": "page", "parameters": {"timeout": 10}},
                        {"action": "retry_original", "target": error_context.target_selector}
                    ],
                    success_probability=0.7,
                    estimated_time=15
                )
            ],
            
            ErrorType.SELECTOR_NOT_FOUND: [
                RecoveryStrategy(
                    strategy_name="wait_and_retry_selector",
                    steps=[
                        {"action": "wait", "target": "page", "parameters": {"timeout": 5}},
                        {"action": "find_alternative_selector", "target": error_context.target_selector}
                    ],
                    success_probability=0.6,
                    estimated_time=10
                ),
                RecoveryStrategy(
                    strategy_name="page_reload_and_retry",
                    steps=[
                        {"action": "reload", "target": "page"},
                        {"action": "wait", "target": "page", "parameters": {"timeout": 5}},
                        {"action": "retry_original", "target": error_context.target_selector}
                    ],
                    success_probability=0.5,
                    estimated_time=20
                )
            ],
            
            ErrorType.ELEMENT_NOT_CLICKABLE: [
                RecoveryStrategy(
                    strategy_name="scroll_and_click",
                    steps=[
                        {"action": "scroll_into_view", "target": error_context.target_selector},
                        {"action": "wait", "target": "element", "parameters": {"timeout": 2}},
                        {"action": "click", "target": error_context.target_selector}
                    ],
                    success_probability=0.8,
                    estimated_time=8
                ),
                RecoveryStrategy(
                    strategy_name="remove_overlays_and_click",
                    steps=[
                        {"action": "remove_overlays", "target": "page"},
                        {"action": "click", "target": error_context.target_selector}
                    ],
                    success_probability=0.7,
                    estimated_time=5
                )
            ],
            
            ErrorType.RATE_LIMITED: [
                RecoveryStrategy(
                    strategy_name="exponential_backoff",
                    steps=[
                        {"action": "wait", "target": "page", "parameters": {"timeout": min(60, 2 ** error_context.retry_count * 5)}},
                        {"action": "retry_original", "target": error_context.target_selector}
                    ],
                    success_probability=0.6,
                    estimated_time=min(60, 2 ** error_context.retry_count * 5)
                )
            ],
            
            ErrorType.NETWORK_ERROR: [
                RecoveryStrategy(
                    strategy_name="network_retry",
                    steps=[
                        {"action": "wait", "target": "page", "parameters": {"timeout": 10}},
                        {"action": "reload", "target": "page"},
                        {"action": "wait_for_load", "target": "page"}
                    ],
                    success_probability=0.5,
                    estimated_time=20
                )
            ]
        }
        
        return default_strategies.get(error_context.error_type, [
            RecoveryStrategy(
                strategy_name="generic_retry",
                steps=[
                    {"action": "wait", "target": "page", "parameters": {"timeout": 5}},
                    {"action": "retry_original", "target": error_context.target_selector}
                ],
                success_probability=0.3,
                estimated_time=10
            )
        ])

    async def _execute_recovery_strategy(self, page: Page, strategy: RecoveryStrategy, error_context: ErrorContext) -> Dict[str, Any]:
        """Execute a specific recovery strategy"""
        
        try:
            for step in strategy.steps:
                action = step.get("action")
                target = step.get("target")
                parameters = step.get("parameters", {})
                
                print(f"  🔄 Executing step: {action}")
                
                if action == "wait":
                    timeout = parameters.get("timeout", 5)
                    await asyncio.sleep(timeout)
                
                elif action == "reload":
                    await page.reload()
                    
                elif action == "wait_for_load":
                    await page.wait_for_load_state("domcontentloaded", timeout=15000)
                
                elif action == "scroll_into_view":
                    if target:
                        try:
                            await page.evaluate(f"document.querySelector('{target}').scrollIntoView()")
                        except:
                            pass
                
                elif action == "remove_overlays":
                    # Remove common overlay elements
                    overlay_selectors = [
                        ".modal", ".overlay", ".popup", ".dialog", 
                        "[style*='z-index']", ".loading", ".spinner"
                    ]
                    
                    for selector in overlay_selectors:
                        try:
                            await page.evaluate(f"""
                                document.querySelectorAll('{selector}').forEach(el => {{
                                    if (el.style.zIndex > 100) el.remove();
                                }});
                            """)
                        except:
                            pass
                
                elif action == "click":
                    if target:
                        await page.click(target)
                
                elif action == "find_alternative_selector":
                    # This would involve finding alternative selectors using AI
                    # For now, we'll try common variations
                    if target:
                        alternative_found = await self._try_alternative_selectors(page, target)
                        if not alternative_found:
                            return {"success": False, "error": "No alternative selector found"}
                
                elif action == "retry_original":
                    # This would depend on the original action that failed
                    # For now, return success to indicate we should retry the original action
                    return {"success": True, "method": "retry_original"}
                
                # Wait between steps
                await asyncio.sleep(1)
            
            return {"success": True, "method": strategy.strategy_name}
            
        except Exception as e:
            return {"success": False, "error": f"Strategy execution failed: {str(e)}"}

    async def _try_alternative_selectors(self, page: Page, original_selector: str) -> bool:
        """Try alternative selectors for the same element"""
        
        # Generate common selector variations
        alternatives = []
        
        # If it's an ID selector, try class alternatives
        if original_selector.startswith("#"):
            element_id = original_selector[1:]
            alternatives.extend([
                f"[id='{element_id}']",
                f"*[id*='{element_id}']",
                f".{element_id}",
                f"[class*='{element_id}']"
            ])
        
        # If it's a class selector, try ID alternatives
        elif original_selector.startswith("."):
            class_name = original_selector[1:]
            alternatives.extend([
                f"#{class_name}",
                f"[class='{class_name}']",
                f"[class*='{class_name}']"
            ])
        
        # Try data attributes
        if "submit" in original_selector.lower():
            alternatives.extend([
                "[type='submit']",
                "input[type='submit']",
                "button[type='submit']",
                "button:contains('Submit')",
                "[data-action='submit']"
            ])
        
        if "login" in original_selector.lower():
            alternatives.extend([
                "[data-action='login']",
                "button:contains('Login')",
                "button:contains('Sign in')",
                ".login-button",
                "#login-btn"
            ])
        
        # Test each alternative
        for alt_selector in alternatives:
            try:
                element = await page.query_selector(alt_selector)
                if element:
                    # Check if element is visible and clickable
                    is_visible = await element.is_visible()
                    if is_visible:
                        print(f"  ✅ Found alternative selector: {alt_selector}")
                        return True
            except:
                continue
        
        return False

    def _update_recovery_stats(self, method: str, success: bool):
        """Update recovery statistics"""
        
        if method not in self.recovery_stats["recovery_methods"]:
            self.recovery_stats["recovery_methods"][method] = {
                "attempts": 0,
                "successes": 0,
                "failures": 0,
                "success_rate": 0.0
            }
        
        stats = self.recovery_stats["recovery_methods"][method]
        stats["attempts"] += 1
        
        if success:
            stats["successes"] += 1
        else:
            stats["failures"] += 1
        
        stats["success_rate"] = stats["successes"] / stats["attempts"]

    async def smart_retry_with_backoff(self, page: Page, action_func: Callable, max_retries: int = 3, initial_delay: float = 1.0) -> Dict[str, Any]:
        """Smart retry mechanism with exponential backoff"""
        
        retry_count = 0
        last_error = None
        
        while retry_count < max_retries:
            try:
                result = await action_func(page)
                
                if result.get("success", True):
                    return {
                        "success": True,
                        "result": result,
                        "retry_count": retry_count
                    }
                else:
                    last_error = result.get("error", "Unknown error")
                    
            except Exception as e:
                last_error = str(e)
                print(f"⚠️ Attempt {retry_count + 1} failed: {last_error}")
            
            retry_count += 1
            
            if retry_count < max_retries:
                # Exponential backoff with jitter
                delay = initial_delay * (2 ** retry_count) + (asyncio.get_event_loop().time() % 1)
                print(f"⏳ Waiting {delay:.1f}s before retry {retry_count + 1}...")
                await asyncio.sleep(delay)
        
        return {
            "success": False,
            "error": f"All {max_retries} retry attempts failed. Last error: {last_error}",
            "retry_count": retry_count
        }

    def get_recovery_statistics(self) -> Dict[str, Any]:
        """Get error recovery statistics"""
        
        success_rate = 0.0
        if self.recovery_stats["total_errors"] > 0:
            success_rate = self.recovery_stats["successful_recoveries"] / self.recovery_stats["total_errors"]
        
        return {
            "total_errors": self.recovery_stats["total_errors"],
            "successful_recoveries": self.recovery_stats["successful_recoveries"],
            "failed_recoveries": self.recovery_stats["failed_recoveries"],
            "overall_success_rate": success_rate,
            "recovery_methods": dict(self.recovery_stats["recovery_methods"]),
            "error_history_count": len(self.error_history),
            "most_common_errors": self._get_most_common_errors()
        }

    def _get_most_common_errors(self) -> Dict[str, int]:
        """Get most common error types"""
        
        error_counts = {}
        for error in self.error_history[-50:]:  # Last 50 errors
            error_type = error.error_type.value
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        return dict(sorted(error_counts.items(), key=lambda x: x[1], reverse=True))

    async def handle_specific_website_errors(self, page: Page, website_domain: str, error_context: ErrorContext) -> Dict[str, Any]:
        """Handle errors specific to certain websites"""
        
        website_specific_strategies = {
            "amazon": {
                "captcha_required": [
                    RecoveryStrategy(
                        strategy_name="amazon_captcha_handling",
                        steps=[
                            {"action": "wait", "parameters": {"timeout": 10}},
                            {"action": "solve_captcha", "target": ".cvf-widget"},
                            {"action": "retry_original"}
                        ],
                        success_probability=0.6,
                        estimated_time=30
                    )
                ],
                "rate_limited": [
                    RecoveryStrategy(
                        strategy_name="amazon_rate_limit_handling",
                        steps=[
                            {"action": "wait", "parameters": {"timeout": 300}},  # 5 minutes
                            {"action": "reload"},
                            {"action": "retry_original"}
                        ],
                        success_probability=0.7,
                        estimated_time=320
                    )
                ]
            }
        }
        
        domain_key = None
        for domain in website_specific_strategies.keys():
            if domain in website_domain.lower():
                domain_key = domain
                break
        
        if domain_key:
            specific_strategies = website_specific_strategies[domain_key].get(error_context.error_type.value, [])
            if specific_strategies:
                print(f"🎯 Using {domain_key}-specific recovery strategies")
                
                for strategy in specific_strategies:
                    result = await self._execute_recovery_strategy(page, strategy, error_context)
                    if result.get("success"):
                        return result
        
        # Fall back to general error handling
        return await self.handle_error(page, error_context)