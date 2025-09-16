import asyncio
import json
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Callable
from playwright.async_api import async_playwright, Page
from dotenv import load_dotenv

from ai_page_analyzer import AIPageAnalyzer, PageType, AuthFlowType
from auth_flow_manager import AuthFlowManager, AuthCredentials
from dynamic_navigator import DynamicNavigator, NavigationGoal
from captcha_handler import CaptchaHandler
from error_recovery_system import ErrorRecoverySystem, ErrorContext, ErrorType
from test_extract_selector import extract_all_selectors
from utilities_local_ai import local_ai_selector_categorizer
from main import group_selectors_by_category

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

@dataclass
class ScrapingSession:
    target_url: str
    credentials: AuthCredentials
    goals: List[NavigationGoal]
    model_name: str = "qwen/qwen3-4b-2507"
    headless: bool = False
    slow_mo: int = 1000
    timeout: int = 15000

class EnhancedWebScraper:
    """Enhanced AI-powered web scraper with comprehensive capabilities"""
    
    def __init__(self, session: ScrapingSession):
        self.session = session
        self.ai_analyzer = AIPageAnalyzer(session.model_name)
        self.auth_manager = AuthFlowManager(session.model_name)
        self.navigator = DynamicNavigator(session.model_name)
        self.captcha_handler = CaptchaHandler(session.model_name)
        self.error_recovery = ErrorRecoverySystem(session.model_name)
        
        # Session state
        self.current_page = None
        self.browser = None
        self.is_authenticated = False
        self.session_history = []
        self.errors_encountered = []

    async def start_scraping_session(self) -> Dict[str, Any]:
        """Start comprehensive scraping session"""
        
        print("🚀 Starting Enhanced AI Web Scraping Session")
        print(f"🌐 Target URL: {self.session.target_url}")
        print(f"🤖 AI Model: {self.session.model_name}")
        print(f"🎯 Goals: {[goal.goal_name for goal in self.session.goals]}")
        
        session_result = {
            "success": False,
            "goals_completed": [],
            "goals_failed": [],
            "total_errors": 0,
            "authentication_status": "not_attempted",
            "session_duration": 0,
            "pages_visited": []
        }
        
        start_time = asyncio.get_event_loop().time()
        
        try:
            async with async_playwright() as p:
                # Launch browser
                self.browser = await p.chromium.launch(
                    headless=self.session.headless, 
                    slow_mo=self.session.slow_mo
                )
                
                self.current_page = await self.browser.new_page()
                self.current_page.set_default_timeout(self.session.timeout)
                
                # Navigate to initial URL
                await self._safe_navigate(self.session.target_url)
                
                # Initial page analysis
                await self._analyze_and_log_page("initial_load")
                
                # Handle authentication if needed
                if self.session.credentials and not self.is_authenticated:
                    auth_result = await self._handle_authentication()
                    session_result["authentication_status"] = "success" if auth_result.get("success") else "failed"
                    
                    if not auth_result.get("success"):
                        print(f"❌ Authentication failed: {auth_result.get('error')}")
                        return session_result
                    
                    self.is_authenticated = True
                    await self._analyze_and_log_page("post_authentication")
                
                # Execute goals
                for goal in self.session.goals:
                    print(f"\n🎯 Executing goal: {goal.goal_name}")
                    
                    goal_result = await self._execute_goal_with_recovery(goal)
                    
                    if goal_result.get("success"):
                        session_result["goals_completed"].append(goal.goal_name)
                        print(f"✅ Goal completed: {goal.goal_name}")
                    else:
                        session_result["goals_failed"].append({
                            "goal": goal.goal_name,
                            "error": goal_result.get("error")
                        })
                        print(f"❌ Goal failed: {goal.goal_name} - {goal_result.get('error')}")
                
                # Final analysis
                await self._analyze_and_log_page("session_end")
                
                session_result["success"] = len(session_result["goals_completed"]) > 0
                
        except Exception as e:
            print(f"💥 Session error: {str(e)}")
            session_result["error"] = str(e)
        
        finally:
            # Cleanup
            if self.browser:
                print("⏳ Waiting before closing browser...")
                await asyncio.sleep(30)  # Give time to review results
                await self.browser.close()
        
        # Session summary
        end_time = asyncio.get_event_loop().time()
        session_result["session_duration"] = end_time - start_time
        session_result["total_errors"] = len(self.errors_encountered)
        session_result["pages_visited"] = [entry["url"] for entry in self.session_history]
        
        print("\n📊 Session Summary:")
        print(f"✅ Goals completed: {len(session_result['goals_completed'])}")
        print(f"❌ Goals failed: {len(session_result['goals_failed'])}")
        print(f"🕐 Session duration: {session_result['session_duration']:.1f}s")
        print(f"🚨 Errors encountered: {session_result['total_errors']}")
        
        return session_result

    async def _handle_authentication(self) -> Dict[str, Any]:
        """Handle authentication with comprehensive error handling"""
        
        print("🔐 Starting authentication process...")
        
        try:
            html_content = await self.current_page.content()
            
            # Check for CAPTCHA first
            captcha_result = await self.captcha_handler.solve_captcha_challenge(self.current_page, html_content)
            
            if captcha_result.get("captcha_present") and not captcha_result.get("success"):
                return {"success": False, "error": "CAPTCHA challenge could not be solved"}
            
            # Proceed with authentication
            auth_result = await self.auth_manager.detect_and_execute_auth_flow(
                self.current_page, 
                self.session.credentials, 
                html_content
            )
            
            # Handle post-auth challenges (2FA, additional verification)
            if auth_result.get("success"):
                await asyncio.sleep(3)  # Allow page to settle
                
                post_auth_html = await self.current_page.content()
                post_auth_result = await self.auth_manager.handle_post_auth_challenges(
                    self.current_page, 
                    post_auth_html
                )
                
                if not post_auth_result.get("success") and post_auth_result.get("challenge_type") != "none":
                    return {"success": False, "error": f"Post-auth challenge failed: {post_auth_result.get('error')}"}
            
            return auth_result
            
        except Exception as e:
            error_context = ErrorContext(
                error_type=ErrorType.AUTHENTICATION_FAILED,
                error_message=str(e),
                current_url=self.current_page.url,
                action_attempted="authentication"
            )
            
            recovery_result = await self.error_recovery.handle_error(self.current_page, error_context)
            
            if recovery_result.get("success"):
                # Retry authentication after recovery
                return await self._handle_authentication()
            else:
                return {"success": False, "error": f"Authentication failed: {str(e)}"}

    async def _execute_goal_with_recovery(self, goal: NavigationGoal) -> Dict[str, Any]:
        """Execute a goal with comprehensive error recovery"""
        
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            try:
                # Check for and handle CAPTCHA before each goal
                html_content = await self.current_page.content()
                captcha_result = await self.captcha_handler.solve_captcha_challenge(self.current_page, html_content)
                
                if captcha_result.get("captcha_present") and not captcha_result.get("success"):
                    print("🛡️ CAPTCHA challenge blocking goal execution")
                    attempt += 1
                    await asyncio.sleep(10)
                    continue
                
                # Execute navigation goal
                goal_result = await self.navigator.navigate_to_goal(self.current_page, goal)
                
                if goal_result.get("success"):
                    return goal_result
                else:
                    # Attempt error recovery
                    error_context = ErrorContext(
                        error_type=self._classify_goal_error(goal_result.get("error", "")),
                        error_message=goal_result.get("error", "Goal execution failed"),
                        current_url=self.current_page.url,
                        action_attempted=f"goal_{goal.goal_name}",
                        retry_count=attempt
                    )
                    
                    recovery_result = await self.error_recovery.handle_error(self.current_page, error_context)
                    
                    if not recovery_result.get("success"):
                        attempt += 1
                        if attempt < max_attempts:
                            print(f"🔄 Retrying goal {goal.goal_name} (attempt {attempt + 1}/{max_attempts})")
                            await asyncio.sleep(5)
                    else:
                        # Recovery successful, retry immediately
                        continue
                
            except Exception as e:
                print(f"❌ Goal execution error: {str(e)}")
                
                error_context = ErrorContext(
                    error_type=ErrorType.UNKNOWN,
                    error_message=str(e),
                    current_url=self.current_page.url,
                    action_attempted=f"goal_{goal.goal_name}",
                    retry_count=attempt
                )
                
                self.errors_encountered.append(error_context)
                attempt += 1
        
        return {"success": False, "error": f"Goal failed after {max_attempts} attempts"}

    async def _safe_navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to URL with error handling"""
        
        try:
            print(f"🌐 Navigating to: {url}")
            await self.current_page.goto(url)
            await self.current_page.wait_for_load_state("domcontentloaded", timeout=self.session.timeout)
            return {"success": True, "url": url}
            
        except Exception as e:
            error_context = ErrorContext(
                error_type=ErrorType.NAVIGATION_FAILED,
                error_message=str(e),
                current_url=url,
                action_attempted="navigation"
            )
            
            recovery_result = await self.error_recovery.handle_error(self.current_page, error_context)
            
            if recovery_result.get("success"):
                return {"success": True, "url": url, "recovered": True}
            else:
                return {"success": False, "error": str(e)}

    async def _analyze_and_log_page(self, stage: str):
        """Analyze current page and log to session history"""
        
        try:
            html_content = await self.current_page.content()
            current_url = self.current_page.url
            
            page_analysis = await self.ai_analyzer.analyze_page_structure(html_content, current_url)
            
            session_entry = {
                "stage": stage,
                "url": current_url,
                "page_type": page_analysis.page_type.value,
                "auth_flow": page_analysis.auth_flow.value if page_analysis.auth_flow else None,
                "available_actions": page_analysis.available_actions,
                "error_messages": page_analysis.error_messages,
                "security_challenges": page_analysis.security_challenges,
                "confidence": page_analysis.confidence,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            self.session_history.append(session_entry)
            
            print(f"📄 Page analysis ({stage}): {page_analysis.page_type.value}")
            if page_analysis.error_messages:
                print(f"⚠️ Page errors: {page_analysis.error_messages}")
            if page_analysis.security_challenges:
                print(f"🛡️ Security challenges: {page_analysis.security_challenges}")
                
        except Exception as e:
            print(f"⚠️ Page analysis failed: {str(e)}")

    def _classify_goal_error(self, error_message: str) -> ErrorType:
        """Classify error type from error message"""
        
        error_message_lower = error_message.lower()
        
        if "timeout" in error_message_lower:
            return ErrorType.TIMEOUT
        elif "selector" in error_message_lower or "not found" in error_message_lower:
            return ErrorType.SELECTOR_NOT_FOUND
        elif "clickable" in error_message_lower:
            return ErrorType.ELEMENT_NOT_CLICKABLE
        elif "navigation" in error_message_lower:
            return ErrorType.NAVIGATION_FAILED
        elif "captcha" in error_message_lower:
            return ErrorType.CAPTCHA_REQUIRED
        elif "rate" in error_message_lower or "limit" in error_message_lower:
            return ErrorType.RATE_LIMITED
        elif "network" in error_message_lower:
            return ErrorType.NETWORK_ERROR
        else:
            return ErrorType.UNKNOWN

    # Convenience methods for common scraping tasks
    
    async def smart_search(self, search_term: str, search_context: str = "") -> Dict[str, Any]:
        """Perform intelligent search"""
        return await self.navigator.smart_search(self.current_page, search_term, search_context)
    
    async def interact_with_product(self, interaction_type: str, product_context: str = "") -> Dict[str, Any]:
        """Interact with product elements"""
        return await self.navigator.smart_product_interaction(self.current_page, interaction_type, product_context)
    
    async def fill_dynamic_form(self, form_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fill forms intelligently"""
        return await self.navigator.handle_dynamic_forms(self.current_page, form_data)

# Example usage functions

async def create_amazon_scraping_session():
    """Create an Amazon scraping session"""
    
    credentials = AuthCredentials(
        email=os.getenv("AMAZON_USERNAME"),
        password=os.getenv("AMAZON_PASSWORD")
    )
    
    goals = [
        NavigationGoal(
            goal_name="login_to_account",
            description="Login to Amazon account with provided credentials",
            success_criteria=["url_contains:amazon", "page_type:home"],
            max_steps=10,
            timeout=60
        ),
        NavigationGoal(
            goal_name="search_product",
            description="Search for sony camera products",
            success_criteria=["page_type:search_results", "text_visible:sony"],
            max_steps=5,
            timeout=30
        ),
        NavigationGoal(
            goal_name="view_product_details",
            description="Click on first product to view details",
            success_criteria=["page_type:product_detail"],
            max_steps=3,
            timeout=20
        )
    ]
    
    session = ScrapingSession(
        target_url="https://www.amazon.in",
        credentials=credentials,
        goals=goals,
        model_name="qwen/qwen3-4b-2507",
        headless=False,
        slow_mo=1000
    )
    
    return session

async def create_general_ecommerce_session(url: str, search_term: str):
    """Create a general e-commerce scraping session"""
    
    goals = [
        NavigationGoal(
            goal_name="analyze_homepage",
            description="Analyze homepage and identify key elements",
            success_criteria=["page_type:home"],
            max_steps=2,
            timeout=20
        ),
        NavigationGoal(
            goal_name="search_products",
            description=f"Search for {search_term}",
            success_criteria=["page_type:search_results"],
            max_steps=5,
            timeout=30
        ),
        NavigationGoal(
            goal_name="browse_products",
            description="Browse through search results and analyze products",
            success_criteria=["page_type:product_listing"],
            max_steps=8,
            timeout=45
        )
    ]
    
    session = ScrapingSession(
        target_url=url,
        credentials=None,  # No authentication needed
        goals=goals,
        headless=False
    )
    
    return session

async def main():
    """Main execution function"""
    
    # Choose scraping session type
    session_type = os.getenv("SESSION_TYPE", "amazon")  # amazon, general, custom
    
    if session_type == "amazon":
        session = await create_amazon_scraping_session()
    elif session_type == "general":
        target_url = os.getenv("TARGET_URL", "https://example-ecommerce.com")
        search_term = os.getenv("SEARCH_TERM", "laptop")
        session = await create_general_ecommerce_session(target_url, search_term)
    else:
        print("❌ Unknown session type. Please set SESSION_TYPE environment variable.")
        return
    
    # Create and run enhanced scraper
    scraper = EnhancedWebScraper(session)
    result = await scraper.start_scraping_session()
    
    # Display results
    print("\n" + "="*50)
    print("📊 FINAL RESULTS")
    print("="*50)
    print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())