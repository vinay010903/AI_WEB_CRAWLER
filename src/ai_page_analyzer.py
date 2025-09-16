import asyncio
import json
import httpx
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

class AuthFlowType(Enum):
    USERNAME_PASSWORD = "username_password"
    USERNAME_OTP = "username_otp"
    EMAIL_PASSWORD = "email_password"
    EMAIL_OTP = "email_otp"
    PHONE_OTP = "phone_otp"
    TWO_FACTOR = "two_factor"
    SOCIAL_LOGIN = "social_login"
    PASSWORDLESS = "passwordless"
    CAPTCHA_REQUIRED = "captcha_required"
    UNKNOWN = "unknown"

class PageType(Enum):
    LOGIN = "login"
    SIGNUP = "signup"
    HOME = "home"
    PRODUCT_LISTING = "product_listing"
    PRODUCT_DETAIL = "product_detail"
    CART = "cart"
    CHECKOUT = "checkout"
    PROFILE = "profile"
    SEARCH_RESULTS = "search_results"
    OTP_VERIFICATION = "otp_verification"
    TWO_FACTOR_AUTH = "two_factor_auth"
    ERROR = "error"
    UNKNOWN = "unknown"

@dataclass
class PageAnalysis:
    page_type: PageType
    auth_flow: Optional[AuthFlowType]
    available_actions: List[str]
    required_inputs: List[Dict[str, Any]]
    navigation_options: List[Dict[str, Any]]
    error_messages: List[str]
    security_challenges: List[str]
    confidence: float

class AIPageAnalyzer:
    def __init__(self, model_name: str = "openai/gpt-oss-20b", timeout: int = 120):
        self.model_name = model_name
        self.timeout = timeout
        self.base_url = "http://localhost:1234/v1/chat/completions"

    async def analyze_page_structure(self, html_content: str, url: str = "") -> PageAnalysis:
        """Analyze page structure and determine page type, auth flow, and available actions"""
        
        analysis_prompt = f"""
        Analyze this webpage and provide a detailed analysis in JSON format.
        
        URL: {url}
        
        HTML Content (first 10000 chars): {html_content[:10000]}
        
        Please analyze and return JSON with:
        {{
            "page_type": "one of: login, signup, home, product_listing, product_detail, cart, checkout, profile, search_results, otp_verification, two_factor_auth, error, unknown",
            "auth_flow": "one of: username_password, username_otp, email_password, email_otp, phone_otp, two_factor, social_login, passwordless, captcha_required, unknown, null",
            "available_actions": ["list of possible actions like 'login', 'search', 'add_to_cart', 'navigate_to_product', etc."],
            "required_inputs": [
                {{
                    "type": "username/email/password/otp/search/etc",
                    "label": "visible label or placeholder",
                    "required": true/false,
                    "selector_hints": ["class names, ids, or other identifying features"]
                }}
            ],
            "navigation_options": [
                {{
                    "action": "what this does",
                    "text": "button/link text",
                    "type": "button/link/form_submit",
                    "selector_hints": ["identifying features"]
                }}
            ],
            "error_messages": ["any visible error messages"],
            "security_challenges": ["captcha", "rate_limit", "suspicious_activity", etc.],
            "confidence": 0.85
        }}
        
        Focus on:
        1. Authentication flow detection (traditional login vs OTP vs 2FA)
        2. Input field identification (username, email, password, OTP, search)
        3. Action buttons (login, continue, submit, search, add to cart)
        4. Navigation elements (menu items, breadcrumbs, pagination)
        5. Security elements (captcha, error messages, blocking)
        6. E-commerce elements (products, prices, cart, checkout)
        """
        
        try:
            analysis_result = await self._query_ai(analysis_prompt)
            return self._parse_page_analysis(analysis_result)
        except Exception as e:
            return PageAnalysis(
                page_type=PageType.UNKNOWN,
                auth_flow=None,
                available_actions=[],
                required_inputs=[],
                navigation_options=[],
                error_messages=[f"Analysis failed: {str(e)}"],
                security_challenges=[],
                confidence=0.0
            )

    async def detect_authentication_method(self, selectors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Detect what type of authentication is being used"""
        
        selectors_json = json.dumps(selectors[:50], indent=2)  # Limit to avoid token limits
        
        auth_prompt = f"""
        Analyze these selectors to determine the authentication method being used.
        
        Selectors: {selectors_json}
        
        Return JSON:
        {{
            "auth_type": "username_password/email_otp/phone_otp/social_login/two_factor/passwordless/unknown",
            "steps_required": ["step1", "step2", "step3"],
            "inputs_needed": [
                {{
                    "step": 1,
                    "type": "username/email/phone/password/otp/2fa_code",
                    "selector": "best_matching_selector",
                    "placeholder_text": "placeholder or label text"
                }}
            ],
            "buttons_sequence": [
                {{
                    "step": 1,
                    "action": "continue/submit/login/send_otp",
                    "selector": "button_selector",
                    "text": "button text"
                }}
            ],
            "social_options": ["google", "facebook", "apple", "etc"],
            "confidence": 0.9
        }}
        
        Look for:
        - Input types (email, password, tel, text)
        - Button text ("Continue", "Send OTP", "Login", "Sign in with Google")
        - Field labels and placeholders
        - Form structure (single form vs multiple steps)
        - Social login buttons
        """
        
        try:
            result = await self._query_ai(auth_prompt)
            return json.loads(result) if isinstance(result, str) else result
        except Exception:
            return {"auth_type": "unknown", "confidence": 0.0}

    async def find_best_selector(self, selectors: List[Dict[str, Any]], task: str, context: str = "") -> Dict[str, Any]:
        """Find the best selector for a specific task using AI"""
        
        selectors_json = json.dumps(selectors[:30], indent=2)
        
        selector_prompt = f"""
        Find the BEST selector for: {task}
        
        Context: {context}
        
        Available selectors: {selectors_json}
        
        Task examples:
        - "click_login_button" - find login/sign in button
        - "fill_username" - find username/email input
        - "fill_password" - find password input
        - "fill_otp" - find OTP/verification code input
        - "click_continue" - find continue/next button
        - "click_submit" - find submit/login button
        - "search_product" - find search input box
        - "add_to_cart" - find add to cart button
        - "navigate_menu" - find navigation menu items
        
        Return JSON:
        {{
            "best_selector": "exact_selector_string",
            "selector_type": "id/class/xpath/css",
            "confidence": 0.95,
            "reasoning": "why this selector was chosen",
            "alternatives": ["backup_selector1", "backup_selector2"]
        }}
        
        Choose based on:
        1. Text content relevance
        2. Element type appropriateness
        3. Selector specificity and reliability
        4. Context clues (form structure, page layout)
        """
        
        try:
            result = await self._query_ai(selector_prompt)
            return json.loads(result) if isinstance(result, str) else result
        except Exception:
            return {"best_selector": None, "confidence": 0.0}

    async def generate_navigation_strategy(self, current_page: PageAnalysis, goal: str) -> Dict[str, Any]:
        """Generate a strategy to achieve a specific goal on the current page"""
        
        strategy_prompt = f"""
        Current page analysis:
        - Page type: {current_page.page_type.value}
        - Auth flow: {current_page.auth_flow.value if current_page.auth_flow else 'None'}
        - Available actions: {current_page.available_actions}
        - Required inputs: {json.dumps(current_page.required_inputs, indent=2)}
        - Navigation options: {json.dumps(current_page.navigation_options, indent=2)}
        - Errors: {current_page.error_messages}
        - Security challenges: {current_page.security_challenges}
        
        Goal: {goal}
        
        Generate a step-by-step strategy to achieve this goal:
        
        Return JSON:
        {{
            "strategy_name": "descriptive name",
            "steps": [
                {{
                    "step_number": 1,
                    "action": "fill_input/click_button/wait/navigate/etc",
                    "target": "selector or element description",
                    "value": "value to input (if applicable)",
                    "wait_condition": "what to wait for after this step",
                    "timeout": 10,
                    "error_handling": "what to do if this step fails"
                }}
            ],
            "success_indicators": ["url_contains", "element_visible", "text_present"],
            "failure_indicators": ["error_message", "timeout", "element_missing"],
            "estimated_time": 30,
            "confidence": 0.85
        }}
        
        Common goals:
        - "login_with_credentials"
        - "search_for_product" 
        - "add_product_to_cart"
        - "complete_checkout"
        - "verify_otp"
        - "handle_two_factor"
        """
        
        try:
            result = await self._query_ai(strategy_prompt)
            return json.loads(result) if isinstance(result, str) else result
        except Exception:
            return {"steps": [], "confidence": 0.0}

    async def analyze_errors_and_suggest_fixes(self, error_context: str, page_content: str = "") -> Dict[str, Any]:
        """Analyze errors and suggest fixes"""
        
        error_prompt = f"""
        Error context: {error_context}
        
        Page content (first 5000 chars): {page_content[:5000]}
        
        Analyze this error and suggest fixes:
        
        Return JSON:
        {{
            "error_type": "selector_not_found/timeout/captcha/rate_limit/authentication_failed/network_error/etc",
            "root_cause": "detailed explanation",
            "suggested_fixes": [
                {{
                    "fix_type": "retry/wait/change_selector/solve_captcha/etc",
                    "description": "what to do",
                    "implementation": "how to implement this fix",
                    "success_probability": 0.8
                }}
            ],
            "alternative_approaches": ["different ways to achieve the same goal"],
            "prevention_tips": ["how to avoid this error in future"]
        }}
        """
        
        try:
            result = await self._query_ai(error_prompt)
            return json.loads(result) if isinstance(result, str) else result
        except Exception:
            return {"error_type": "analysis_failed", "suggested_fixes": []}

    async def _query_ai(self, prompt: str) -> Any:
        """Send query to local AI model"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {
                    "model": self.model_name,
                    "messages": [
                        {"role": "system", "content": "You are an expert web scraping and automation assistant. Always return valid JSON responses with no additional text or formatting."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 4000,
                    "temperature": 0.3
                }
                
                response = await client.post(self.base_url, json=payload)
                result = response.json()["choices"][0]["message"]["content"]
                
                # Clean up JSON formatting
                if result.startswith("```json"):
                    result = result[7:]
                if result.endswith("```"):
                    result = result[:-3]
                result = result.strip()
                
                return json.loads(result)
                
        except Exception as e:
            raise Exception(f"AI query failed: {str(e)}")

    def _parse_page_analysis(self, analysis_data: Dict[str, Any]) -> PageAnalysis:
        """Parse AI response into PageAnalysis object"""
        try:
            return PageAnalysis(
                page_type=PageType(analysis_data.get("page_type", "unknown")),
                auth_flow=AuthFlowType(analysis_data.get("auth_flow")) if analysis_data.get("auth_flow") else None,
                available_actions=analysis_data.get("available_actions", []),
                required_inputs=analysis_data.get("required_inputs", []),
                navigation_options=analysis_data.get("navigation_options", []),
                error_messages=analysis_data.get("error_messages", []),
                security_challenges=analysis_data.get("security_challenges", []),
                confidence=analysis_data.get("confidence", 0.0)
            )
        except Exception:
            return PageAnalysis(
                page_type=PageType.UNKNOWN,
                auth_flow=None,
                available_actions=[],
                required_inputs=[],
                navigation_options=[],
                error_messages=["Failed to parse analysis"],
                security_challenges=[],
                confidence=0.0
            )