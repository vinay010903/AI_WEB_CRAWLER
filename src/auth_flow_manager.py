import asyncio
import json
import time
import os
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from abc import ABC, abstractmethod
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout

from ai_page_analyzer import AIPageAnalyzer, AuthFlowType, PageType, PageAnalysis

@dataclass
class AuthCredentials:
    username: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    otp: Optional[str] = None
    two_factor_code: Optional[str] = None
    backup_codes: Optional[List[str]] = None
    social_provider: Optional[str] = None

@dataclass
class AuthStep:
    step_number: int
    action: str  # fill_input, click_button, wait_for_otp, etc.
    target_selector: str
    value: Optional[str] = None
    wait_condition: Optional[str] = None
    timeout: int = 10
    retry_count: int = 3
    success_indicators: List[str] = None
    failure_indicators: List[str] = None

class AuthFlowHandler(ABC):
    def __init__(self, ai_analyzer: AIPageAnalyzer):
        self.ai_analyzer = ai_analyzer
        self.max_retries = 3
        self.step_timeout = 15

    @abstractmethod
    async def can_handle(self, page_analysis: PageAnalysis) -> bool:
        """Check if this handler can process the current page"""
        pass

    @abstractmethod
    async def execute_auth_flow(self, page: Page, credentials: AuthCredentials, grouped_selectors: Dict) -> Dict[str, Any]:
        """Execute the authentication flow"""
        pass

    async def find_selector_with_ai(self, grouped_selectors: Dict, task: str, context: str = "") -> Optional[str]:
        """Find the best selector for a task using AI"""
        all_selectors = []
        for category, selectors in grouped_selectors.items():
            all_selectors.extend(selectors)
        
        if not all_selectors:
            return None
            
        result = await self.ai_analyzer.find_best_selector(all_selectors, task, context)
        return result.get("best_selector")

    async def wait_for_page_change(self, page: Page, timeout: int = 10) -> bool:
        """Wait for page to change after an action"""
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=timeout * 1000)
            return True
        except:
            return False

class UsernamePasswordHandler(AuthFlowHandler):
    """Traditional username/password authentication"""
    
    async def can_handle(self, page_analysis: PageAnalysis) -> bool:
        return page_analysis.auth_flow == AuthFlowType.USERNAME_PASSWORD

    async def execute_auth_flow(self, page: Page, credentials: AuthCredentials, grouped_selectors: Dict) -> Dict[str, Any]:
        print("🔐 Executing Username/Password authentication flow")
        
        try:
            # Step 1: Find and fill username
            username_selector = await self.find_selector_with_ai(
                grouped_selectors, 
                "fill_username", 
                "Find input field for username or email"
            )
            
            if not username_selector:
                return {"success": False, "error": "Username selector not found"}
            
            username_value = credentials.username or credentials.email
            if not username_value:
                return {"success": False, "error": "No username/email provided"}
            
            await page.fill(username_selector, username_value)
            print(f"✅ Username filled: {username_selector}")
            
            # Step 2: Find and fill password
            password_selector = await self.find_selector_with_ai(
                grouped_selectors,
                "fill_password",
                "Find password input field"
            )
            
            if not password_selector:
                return {"success": False, "error": "Password selector not found"}
            
            if not credentials.password:
                return {"success": False, "error": "No password provided"}
            
            await page.fill(password_selector, credentials.password)
            print(f"✅ Password filled: {password_selector}")
            
            # Step 3: Find and click submit button
            submit_selector = await self.find_selector_with_ai(
                grouped_selectors,
                "click_submit",
                "Find login or submit button"
            )
            
            if not submit_selector:
                return {"success": False, "error": "Submit button not found"}
            
            await page.click(submit_selector)
            print(f"✅ Submit clicked: {submit_selector}")
            
            # Wait for navigation
            await self.wait_for_page_change(page, 15)
            
            return {"success": True, "flow_type": "username_password"}
            
        except Exception as e:
            return {"success": False, "error": f"Username/Password flow failed: {str(e)}"}

class EmailOTPHandler(AuthFlowHandler):
    """Email OTP authentication"""
    
    def __init__(self, ai_analyzer: AIPageAnalyzer, otp_callback: Optional[Callable] = None):
        super().__init__(ai_analyzer)
        self.otp_callback = otp_callback  # Function to get OTP from user/email

    async def can_handle(self, page_analysis: PageAnalysis) -> bool:
        return page_analysis.auth_flow in [AuthFlowType.EMAIL_OTP, AuthFlowType.USERNAME_OTP]

    async def execute_auth_flow(self, page: Page, credentials: AuthCredentials, grouped_selectors: Dict) -> Dict[str, Any]:
        print("📧 Executing Email OTP authentication flow")
        
        try:
            # Step 1: Fill email/username
            email_selector = await self.find_selector_with_ai(
                grouped_selectors,
                "fill_username",
                "Find email or username input field"
            )
            
            if not email_selector:
                return {"success": False, "error": "Email selector not found"}
            
            email_value = credentials.email or credentials.username
            if not email_value:
                return {"success": False, "error": "No email/username provided"}
            
            await page.fill(email_selector, email_value)
            print(f"✅ Email filled: {email_selector}")
            
            # Step 2: Send OTP
            send_otp_selector = await self.find_selector_with_ai(
                grouped_selectors,
                "click_continue",
                "Find send OTP or continue button"
            )
            
            if send_otp_selector:
                await page.click(send_otp_selector)
                print(f"✅ Send OTP clicked: {send_otp_selector}")
                await self.wait_for_page_change(page, 10)
            
            # Step 3: Wait for OTP page and fill OTP
            await asyncio.sleep(3)  # Allow page to load
            
            # Re-analyze page for OTP input
            html_content = await page.content()
            from test_extract_selector import extract_all_selectors
            from utilities_local_ai import local_ai_selector_categorizer
            from main import group_selectors_by_category
            
            simple_selectors = extract_all_selectors(html_content, None)
            categorized_selectors = local_ai_selector_categorizer(simple_selectors, "qwen/qwen3-4b-2507")
            otp_grouped_selectors = group_selectors_by_category(simple_selectors, categorized_selectors)
            
            otp_selector = await self.find_selector_with_ai(
                otp_grouped_selectors,
                "fill_otp",
                "Find OTP or verification code input field"
            )
            
            if not otp_selector:
                return {"success": False, "error": "OTP input selector not found"}
            
            # Get OTP (from callback, user input, or credentials)
            otp_code = None
            if self.otp_callback:
                otp_code = await self.otp_callback()
            elif credentials.otp:
                otp_code = credentials.otp
            else:
                # Wait for user to manually enter OTP or implement email checking
                print("⏳ Waiting for OTP... (implement email checking or manual input)")
                await asyncio.sleep(30)  # Give user time to enter manually
                return {"success": False, "error": "OTP not provided"}
            
            if otp_code:
                await page.fill(otp_selector, otp_code)
                print(f"✅ OTP filled: {otp_selector}")
                
                # Submit OTP
                verify_selector = await self.find_selector_with_ai(
                    otp_grouped_selectors,
                    "click_submit",
                    "Find verify or submit button for OTP"
                )
                
                if verify_selector:
                    await page.click(verify_selector)
                    print(f"✅ OTP verified: {verify_selector}")
                    await self.wait_for_page_change(page, 15)
                
                return {"success": True, "flow_type": "email_otp"}
            
            return {"success": False, "error": "OTP verification failed"}
            
        except Exception as e:
            return {"success": False, "error": f"Email OTP flow failed: {str(e)}"}

class PhoneOTPHandler(AuthFlowHandler):
    """Phone/SMS OTP authentication"""
    
    def __init__(self, ai_analyzer: AIPageAnalyzer, otp_callback: Optional[Callable] = None):
        super().__init__(ai_analyzer)
        self.otp_callback = otp_callback

    async def can_handle(self, page_analysis: PageAnalysis) -> bool:
        return page_analysis.auth_flow == AuthFlowType.PHONE_OTP

    async def execute_auth_flow(self, page: Page, credentials: AuthCredentials, grouped_selectors: Dict) -> Dict[str, Any]:
        print("📱 Executing Phone OTP authentication flow")
        
        try:
            # Step 1: Fill phone number
            phone_selector = await self.find_selector_with_ai(
                grouped_selectors,
                "fill_username",
                "Find phone number input field"
            )
            
            if not phone_selector:
                return {"success": False, "error": "Phone number selector not found"}
            
            if not credentials.phone:
                return {"success": False, "error": "No phone number provided"}
            
            await page.fill(phone_selector, credentials.phone)
            print(f"✅ Phone filled: {phone_selector}")
            
            # Step 2: Send SMS OTP
            send_sms_selector = await self.find_selector_with_ai(
                grouped_selectors,
                "click_continue",
                "Find send SMS or continue button"
            )
            
            if send_sms_selector:
                await page.click(send_sms_selector)
                print(f"✅ Send SMS clicked: {send_sms_selector}")
                await self.wait_for_page_change(page, 10)
            
            # Step 3: Handle SMS OTP (similar to email OTP)
            await asyncio.sleep(3)
            
            html_content = await page.content()
            from test_extract_selector import extract_all_selectors
            from utilities_local_ai import local_ai_selector_categorizer
            from main import group_selectors_by_category
            
            simple_selectors = extract_all_selectors(html_content, None)
            categorized_selectors = local_ai_selector_categorizer(simple_selectors, "qwen/qwen3-4b-2507")
            otp_grouped_selectors = group_selectors_by_category(simple_selectors, categorized_selectors)
            
            otp_selector = await self.find_selector_with_ai(
                otp_grouped_selectors,
                "fill_otp",
                "Find SMS OTP or verification code input field"
            )
            
            if not otp_selector:
                return {"success": False, "error": "SMS OTP input selector not found"}
            
            # Get SMS OTP
            otp_code = None
            if self.otp_callback:
                otp_code = await self.otp_callback()
            elif credentials.otp:
                otp_code = credentials.otp
            else:
                print("⏳ Waiting for SMS OTP...")
                await asyncio.sleep(60)  # Wait longer for SMS
                return {"success": False, "error": "SMS OTP not provided"}
            
            if otp_code:
                await page.fill(otp_selector, otp_code)
                print(f"✅ SMS OTP filled: {otp_selector}")
                
                verify_selector = await self.find_selector_with_ai(
                    otp_grouped_selectors,
                    "click_submit",
                    "Find verify or submit button for SMS OTP"
                )
                
                if verify_selector:
                    await page.click(verify_selector)
                    print(f"✅ SMS OTP verified: {verify_selector}")
                    await self.wait_for_page_change(page, 15)
                
                return {"success": True, "flow_type": "phone_otp"}
            
            return {"success": False, "error": "SMS OTP verification failed"}
            
        except Exception as e:
            return {"success": False, "error": f"Phone OTP flow failed: {str(e)}"}

class TwoFactorHandler(AuthFlowHandler):
    """Two-factor authentication (after initial login)"""
    
    def __init__(self, ai_analyzer: AIPageAnalyzer, two_factor_callback: Optional[Callable] = None):
        super().__init__(ai_analyzer)
        self.two_factor_callback = two_factor_callback

    async def can_handle(self, page_analysis: PageAnalysis) -> bool:
        return (page_analysis.auth_flow == AuthFlowType.TWO_FACTOR or 
                page_analysis.page_type == PageType.TWO_FACTOR_AUTH)

    async def execute_auth_flow(self, page: Page, credentials: AuthCredentials, grouped_selectors: Dict) -> Dict[str, Any]:
        print("🔐 Executing Two-Factor authentication flow")
        
        try:
            # Find 2FA input
            two_fa_selector = await self.find_selector_with_ai(
                grouped_selectors,
                "fill_otp",
                "Find two-factor authentication code input field"
            )
            
            if not two_fa_selector:
                return {"success": False, "error": "2FA input selector not found"}
            
            # Get 2FA code
            two_fa_code = None
            if self.two_factor_callback:
                two_fa_code = await self.two_factor_callback()
            elif credentials.two_factor_code:
                two_fa_code = credentials.two_factor_code
            else:
                print("⏳ Waiting for 2FA code from authenticator app...")
                await asyncio.sleep(30)
                return {"success": False, "error": "2FA code not provided"}
            
            if two_fa_code:
                await page.fill(two_fa_selector, two_fa_code)
                print(f"✅ 2FA code filled: {two_fa_selector}")
                
                verify_selector = await self.find_selector_with_ai(
                    grouped_selectors,
                    "click_submit",
                    "Find verify or continue button for 2FA"
                )
                
                if verify_selector:
                    await page.click(verify_selector)
                    print(f"✅ 2FA verified: {verify_selector}")
                    await self.wait_for_page_change(page, 15)
                
                return {"success": True, "flow_type": "two_factor"}
            
            return {"success": False, "error": "2FA verification failed"}
            
        except Exception as e:
            return {"success": False, "error": f"2FA flow failed: {str(e)}"}

class SocialLoginHandler(AuthFlowHandler):
    """Social login (Google, Facebook, Apple, etc.)"""
    
    async def can_handle(self, page_analysis: PageAnalysis) -> bool:
        return page_analysis.auth_flow == AuthFlowType.SOCIAL_LOGIN

    async def execute_auth_flow(self, page: Page, credentials: AuthCredentials, grouped_selectors: Dict) -> Dict[str, Any]:
        print("🌐 Executing Social Login authentication flow")
        
        try:
            # Find social login buttons
            if not credentials.social_provider:
                return {"success": False, "error": "No social provider specified"}
            
            social_selector = await self.find_selector_with_ai(
                grouped_selectors,
                f"click_social_{credentials.social_provider}",
                f"Find {credentials.social_provider} login button"
            )
            
            if not social_selector:
                return {"success": False, "error": f"{credentials.social_provider} login button not found"}
            
            # Click social login button
            await page.click(social_selector)
            print(f"✅ {credentials.social_provider} login clicked: {social_selector}")
            
            # Handle popup or redirect
            await asyncio.sleep(5)  # Allow for popup or redirect
            
            # Note: Full social login implementation would need to handle:
            # - Popup windows
            # - OAuth redirects
            # - Provider-specific authentication
            # This is a simplified version
            
            return {"success": True, "flow_type": "social_login", "provider": credentials.social_provider}
            
        except Exception as e:
            return {"success": False, "error": f"Social login flow failed: {str(e)}"}

class AuthFlowManager:
    """Main manager for handling different authentication flows"""
    
    def __init__(self, model_name: str = "openai/gpt-oss-20b"):
        self.ai_analyzer = AIPageAnalyzer(model_name)
        self.handlers = [
            UsernamePasswordHandler(self.ai_analyzer),
            EmailOTPHandler(self.ai_analyzer),
            PhoneOTPHandler(self.ai_analyzer),
            TwoFactorHandler(self.ai_analyzer),
            SocialLoginHandler(self.ai_analyzer)
        ]
        
    def set_otp_callback(self, handler_type: str, callback: Callable):
        """Set callback function for OTP/2FA handlers"""
        for handler in self.handlers:
            if handler_type == "email_otp" and isinstance(handler, EmailOTPHandler):
                handler.otp_callback = callback
            elif handler_type == "phone_otp" and isinstance(handler, PhoneOTPHandler):
                handler.otp_callback = callback
            elif handler_type == "two_factor" and isinstance(handler, TwoFactorHandler):
                handler.two_factor_callback = callback

    async def detect_and_execute_auth_flow(self, page: Page, credentials: AuthCredentials, html_content: str) -> Dict[str, Any]:
        """Detect the authentication flow and execute it"""
        
        try:
            # Analyze the page to determine auth flow
            current_url = page.url
            page_analysis = await self.ai_analyzer.analyze_page_structure(html_content, current_url)
            
            print(f"🔍 Detected page type: {page_analysis.page_type.value}")
            print(f"🔐 Detected auth flow: {page_analysis.auth_flow.value if page_analysis.auth_flow else 'None'}")
            
            if page_analysis.error_messages:
                print(f"⚠️ Error messages detected: {page_analysis.error_messages}")
            
            if page_analysis.security_challenges:
                print(f"🛡️ Security challenges: {page_analysis.security_challenges}")
            
            # Extract and group selectors
            from test_extract_selector import extract_all_selectors
            from utilities_local_ai import local_ai_selector_categorizer
            from main import group_selectors_by_category
            
            simple_selectors = extract_all_selectors(html_content, None)
            categorized_selectors = local_ai_selector_categorizer(simple_selectors, "qwen/qwen3-4b-2507")
            grouped_selectors = group_selectors_by_category(simple_selectors, categorized_selectors)
            
            # Find appropriate handler
            for handler in self.handlers:
                if await handler.can_handle(page_analysis):
                    print(f"🎯 Using handler: {handler.__class__.__name__}")
                    result = await handler.execute_auth_flow(page, credentials, grouped_selectors)
                    
                    # Add page analysis info to result
                    result["page_analysis"] = {
                        "page_type": page_analysis.page_type.value,
                        "auth_flow": page_analysis.auth_flow.value if page_analysis.auth_flow else None,
                        "confidence": page_analysis.confidence,
                        "security_challenges": page_analysis.security_challenges
                    }
                    
                    return result
            
            return {
                "success": False, 
                "error": "No suitable authentication handler found",
                "detected_flow": page_analysis.auth_flow.value if page_analysis.auth_flow else "unknown"
            }
            
        except Exception as e:
            return {"success": False, "error": f"Auth flow detection failed: {str(e)}"}

    async def handle_post_auth_challenges(self, page: Page, html_content: str) -> Dict[str, Any]:
        """Handle challenges that appear after initial authentication"""
        
        page_analysis = await self.ai_analyzer.analyze_page_structure(html_content, page.url)
        
        if page_analysis.page_type == PageType.TWO_FACTOR_AUTH:
            # Handle 2FA if detected
            two_fa_handler = TwoFactorHandler(self.ai_analyzer)
            from test_extract_selector import extract_all_selectors
            from utilities_local_ai import local_ai_selector_categorizer
            from main import group_selectors_by_category
            
            simple_selectors = extract_all_selectors(html_content, None)
            categorized_selectors = local_ai_selector_categorizer(simple_selectors, "qwen/qwen3-4b-2507")
            grouped_selectors = group_selectors_by_category(simple_selectors, categorized_selectors)
            
            return await two_fa_handler.execute_auth_flow(page, AuthCredentials(), grouped_selectors)
        
        return {"success": True, "challenge_type": "none"}