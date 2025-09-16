import asyncio
import json
import base64
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from playwright.async_api import Page

from ai_page_analyzer import AIPageAnalyzer

@dataclass
class CaptchaChallenge:
    captcha_type: str  # recaptcha, hcaptcha, image, text, audio, math
    selector: str
    image_data: Optional[str] = None
    challenge_text: Optional[str] = None
    difficulty: float = 0.5
    time_limit: Optional[int] = None

class CaptchaHandler:
    """AI-powered CAPTCHA detection and handling system"""
    
    def __init__(self, model_name: str = "openai/gpt-oss-20b"):
        self.ai_analyzer = AIPageAnalyzer(model_name)
        self.captcha_solving_callback = None
        self.supported_types = [
            "recaptcha_v2", "recaptcha_v3", "hcaptcha", 
            "image_captcha", "text_captcha", "math_captcha",
            "audio_captcha", "cloudflare_turnstile"
        ]

    def set_captcha_solving_callback(self, callback: Callable):
        """Set callback for external CAPTCHA solving service"""
        self.captcha_solving_callback = callback

    async def detect_captcha(self, page: Page, html_content: str) -> Dict[str, Any]:
        """Detect if CAPTCHA is present on the page"""
        
        print("🔍 Scanning for CAPTCHA challenges...")
        
        captcha_detection_prompt = f"""
        Analyze this webpage content and detect any CAPTCHA challenges present.
        
        HTML Content (first 8000 chars): {html_content[:8000]}
        
        Look for:
        1. reCAPTCHA elements (div with class containing 'recaptcha', 'g-recaptcha')
        2. hCaptcha elements (div with class containing 'hcaptcha', 'h-captcha')
        3. Image-based CAPTCHAs (img elements with captcha-related attributes)
        4. Text-based CAPTCHAs (input fields with captcha labels)
        5. Math CAPTCHAs (mathematical expressions to solve)
        6. Cloudflare Turnstile challenges
        7. Custom CAPTCHA implementations
        
        Return JSON:
        {{
            "captcha_detected": true/false,
            "captcha_type": "recaptcha_v2/recaptcha_v3/hcaptcha/image_captcha/text_captcha/math_captcha/audio_captcha/cloudflare_turnstile/custom/none",
            "captcha_elements": [
                {{
                    "type": "specific_captcha_type",
                    "selector": "css_selector_to_element",
                    "site_key": "site_key_if_available",
                    "attributes": {{"key": "value"}},
                    "challenge_text": "visible_challenge_text_if_any",
                    "difficulty": 0.7,
                    "location": "form_section/popup/inline/etc"
                }}
            ],
            "blocking_access": true/false,
            "confidence": 0.9
        }}
        """
        
        try:
            result = await self.ai_analyzer._query_ai(captcha_detection_prompt)
            
            if result.get("captcha_detected"):
                print(f"🛡️ CAPTCHA detected: {result.get('captcha_type')}")
                return result
            else:
                print("✅ No CAPTCHA detected")
                return {"captcha_detected": False, "captcha_type": "none"}
                
        except Exception as e:
            print(f"❌ CAPTCHA detection failed: {e}")
            return {"captcha_detected": False, "error": str(e)}

    async def handle_recaptcha_v2(self, page: Page, captcha_element: Dict) -> Dict[str, Any]:
        """Handle reCAPTCHA v2 challenges"""
        
        print("🔓 Handling reCAPTCHA v2...")
        
        selector = captcha_element.get("selector")
        site_key = captcha_element.get("site_key")
        
        if not selector:
            return {"success": False, "error": "No reCAPTCHA selector provided"}
        
        try:
            # Wait for reCAPTCHA to load
            await page.wait_for_selector(selector, timeout=10000)
            
            # Check if reCAPTCHA iframe is present
            recaptcha_iframe = await page.query_selector("iframe[src*='recaptcha']")
            if recaptcha_iframe:
                print("📱 reCAPTCHA iframe found")
                
                # If callback is available, use external solving service
                if self.captcha_solving_callback:
                    print("🤖 Using external CAPTCHA solving service...")
                    
                    captcha_params = {
                        "type": "recaptcha_v2",
                        "site_key": site_key,
                        "page_url": page.url,
                        "selector": selector
                    }
                    
                    solution = await self.captcha_solving_callback(captcha_params)
                    
                    if solution.get("success"):
                        # Inject solution into page
                        await page.evaluate(f"""
                            document.querySelector('#{selector.replace('#', '')}').value = '{solution.get('token')}';
                            if (window.grecaptcha) {{
                                window.grecaptcha.execute();
                            }}
                        """)
                        
                        return {"success": True, "method": "external_service"}
                    else:
                        return {"success": False, "error": "External service failed"}
                
                # Manual interaction (click checkbox)
                checkbox_selector = "iframe[src*='recaptcha'] ~ div .recaptcha-checkbox-border"
                checkbox = await page.query_selector(checkbox_selector)
                
                if checkbox:
                    await page.click(checkbox_selector)
                    print("✅ reCAPTCHA checkbox clicked")
                    
                    # Wait for challenge or completion
                    await asyncio.sleep(3)
                    
                    # Check if image challenge appeared
                    challenge_iframe = await page.query_selector("iframe[src*='bframe']")
                    if challenge_iframe:
                        return await self._handle_recaptcha_image_challenge(page)
                    else:
                        return {"success": True, "method": "checkbox_only"}
                
            return {"success": False, "error": "reCAPTCHA iframe not found"}
            
        except Exception as e:
            return {"success": False, "error": f"reCAPTCHA v2 handling failed: {str(e)}"}

    async def handle_recaptcha_v3(self, page: Page, captcha_element: Dict) -> Dict[str, Any]:
        """Handle reCAPTCHA v3 (invisible)"""
        
        print("🔓 Handling reCAPTCHA v3...")
        
        try:
            # reCAPTCHA v3 is usually invisible and automatic
            # We mainly need to wait for it to complete
            
            # Wait for potential network requests to complete
            await page.wait_for_load_state("networkidle", timeout=10000)
            
            # Check if there's a score-based verification
            recaptcha_token = await page.evaluate("""
                () => {
                    return new Promise((resolve) => {
                        if (window.grecaptcha && window.grecaptcha.ready) {
                            window.grecaptcha.ready(() => {
                                window.grecaptcha.execute('{}', {action: 'submit'})
                                    .then(token => resolve(token))
                                    .catch(() => resolve(null));
                            });
                        } else {
                            resolve(null);
                        }
                    });
                }
            """.format(captcha_element.get("site_key", "")))
            
            if recaptcha_token:
                print("✅ reCAPTCHA v3 token obtained")
                return {"success": True, "method": "automatic", "token": recaptcha_token}
            else:
                return {"success": False, "error": "Failed to get reCAPTCHA v3 token"}
                
        except Exception as e:
            return {"success": False, "error": f"reCAPTCHA v3 handling failed: {str(e)}"}

    async def handle_hcaptcha(self, page: Page, captcha_element: Dict) -> Dict[str, Any]:
        """Handle hCaptcha challenges"""
        
        print("🔓 Handling hCaptcha...")
        
        selector = captcha_element.get("selector")
        site_key = captcha_element.get("site_key")
        
        try:
            # Wait for hCaptcha to load
            await page.wait_for_selector(selector, timeout=10000)
            
            # If external service available
            if self.captcha_solving_callback:
                captcha_params = {
                    "type": "hcaptcha",
                    "site_key": site_key,
                    "page_url": page.url,
                    "selector": selector
                }
                
                solution = await self.captcha_solving_callback(captcha_params)
                
                if solution.get("success"):
                    await page.evaluate(f"""
                        document.querySelector('[name="h-captcha-response"]').value = '{solution.get('token')}';
                    """)
                    
                    return {"success": True, "method": "external_service"}
            
            # Manual interaction
            hcaptcha_checkbox = await page.query_selector(".hcaptcha-box .hcaptcha-checkbox")
            if hcaptcha_checkbox:
                await page.click(".hcaptcha-box .hcaptcha-checkbox")
                await asyncio.sleep(3)
                
                return {"success": True, "method": "manual_checkbox"}
            
            return {"success": False, "error": "hCaptcha checkbox not found"}
            
        except Exception as e:
            return {"success": False, "error": f"hCaptcha handling failed: {str(e)}"}

    async def handle_image_captcha(self, page: Page, captcha_element: Dict) -> Dict[str, Any]:
        """Handle image-based CAPTCHA"""
        
        print("🖼️ Handling image CAPTCHA...")
        
        selector = captcha_element.get("selector")
        
        try:
            # Find captcha image
            captcha_img = await page.query_selector(f"{selector} img, img[src*='captcha']")
            
            if not captcha_img:
                return {"success": False, "error": "CAPTCHA image not found"}
            
            # Get image data
            image_data = await captcha_img.screenshot(type="png")
            image_base64 = base64.b64encode(image_data).decode()
            
            # Use AI to solve image CAPTCHA
            solution = await self._solve_image_captcha_with_ai(image_base64, captcha_element.get("challenge_text", ""))
            
            if solution.get("success"):
                # Find input field and fill solution
                input_selector = f"{selector} input[type='text']"
                captcha_input = await page.query_selector(input_selector)
                
                if captcha_input:
                    await page.fill(input_selector, solution.get("answer"))
                    print(f"✅ Image CAPTCHA solved: {solution.get('answer')}")
                    return {"success": True, "method": "ai_ocr", "answer": solution.get("answer")}
                else:
                    return {"success": False, "error": "CAPTCHA input field not found"}
            else:
                return {"success": False, "error": "Failed to solve image CAPTCHA"}
                
        except Exception as e:
            return {"success": False, "error": f"Image CAPTCHA handling failed: {str(e)}"}

    async def handle_text_captcha(self, page: Page, captcha_element: Dict) -> Dict[str, Any]:
        """Handle text-based CAPTCHA"""
        
        print("📝 Handling text CAPTCHA...")
        
        selector = captcha_element.get("selector")
        challenge_text = captcha_element.get("challenge_text", "")
        
        try:
            # Use AI to solve text challenge
            solution = await self._solve_text_captcha_with_ai(challenge_text)
            
            if solution.get("success"):
                # Find input and fill answer
                input_selector = f"{selector} input[type='text']"
                await page.fill(input_selector, solution.get("answer"))
                
                print(f"✅ Text CAPTCHA solved: {solution.get('answer')}")
                return {"success": True, "method": "ai_text", "answer": solution.get("answer")}
            else:
                return {"success": False, "error": "Failed to solve text CAPTCHA"}
                
        except Exception as e:
            return {"success": False, "error": f"Text CAPTCHA handling failed: {str(e)}"}

    async def handle_math_captcha(self, page: Page, captcha_element: Dict) -> Dict[str, Any]:
        """Handle mathematical CAPTCHA"""
        
        print("🔢 Handling math CAPTCHA...")
        
        selector = captcha_element.get("selector")
        challenge_text = captcha_element.get("challenge_text", "")
        
        try:
            # Extract math expression
            math_solution = await self._solve_math_captcha(challenge_text)
            
            if math_solution.get("success"):
                input_selector = f"{selector} input[type='text']"
                await page.fill(input_selector, str(math_solution.get("answer")))
                
                print(f"✅ Math CAPTCHA solved: {math_solution.get('answer')}")
                return {"success": True, "method": "math_eval", "answer": math_solution.get("answer")}
            else:
                return {"success": False, "error": "Failed to solve math CAPTCHA"}
                
        except Exception as e:
            return {"success": False, "error": f"Math CAPTCHA handling failed: {str(e)}"}

    async def _handle_recaptcha_image_challenge(self, page: Page) -> Dict[str, Any]:
        """Handle reCAPTCHA image selection challenge"""
        
        print("🖼️ Handling reCAPTCHA image challenge...")
        
        try:
            # Wait for challenge to load
            await asyncio.sleep(2)
            
            # This would require more sophisticated image recognition
            # For now, return failure to indicate manual intervention needed
            print("⚠️ reCAPTCHA image challenge requires manual solving")
            
            return {"success": False, "error": "Image challenge requires manual intervention"}
            
        except Exception as e:
            return {"success": False, "error": f"Image challenge handling failed: {str(e)}"}

    async def _solve_image_captcha_with_ai(self, image_base64: str, challenge_text: str) -> Dict[str, Any]:
        """Solve image CAPTCHA using AI OCR"""
        
        ocr_prompt = f"""
        Analyze this CAPTCHA image and extract the text/characters shown.
        
        Challenge text: {challenge_text}
        Image data: [Base64 image provided]
        
        The image contains text that needs to be recognized. Look for:
        - Distorted letters and numbers
        - Characters with noise/lines
        - Multiple characters in sequence
        - Case-sensitive text
        
        Return JSON:
        {{
            "success": true/false,
            "answer": "extracted_text",
            "confidence": 0.85,
            "character_count": 5,
            "contains_numbers": true/false,
            "contains_letters": true/false
        }}
        
        Be very careful with character recognition:
        - Distinguish between 0 (zero) and O (letter O)
        - Distinguish between 1 (one) and l (lowercase L) and I (uppercase i)
        - Pay attention to case sensitivity
        """
        
        try:
            # Note: This would need actual image processing capabilities
            # For now, return a placeholder response
            return {
                "success": False,
                "error": "OCR functionality not implemented",
                "answer": ""
            }
            
        except Exception as e:
            return {"success": False, "error": f"OCR failed: {str(e)}"}

    async def _solve_text_captcha_with_ai(self, challenge_text: str) -> Dict[str, Any]:
        """Solve text-based CAPTCHA using AI"""
        
        text_solving_prompt = f"""
        Solve this text-based CAPTCHA challenge:
        
        Challenge: {challenge_text}
        
        Common text CAPTCHA types:
        - "What is 5 + 3?" -> Answer: 8
        - "Type the word 'robot'" -> Answer: robot
        - "What color is the sky?" -> Answer: blue
        - "Complete: cat, dog, ___" -> Answer: bird (or similar)
        - "What is the opposite of hot?" -> Answer: cold
        
        Return JSON:
        {{
            "success": true/false,
            "answer": "solution_text",
            "reasoning": "why_this_answer",
            "confidence": 0.9
        }}
        """
        
        try:
            result = await self.ai_analyzer._query_ai(text_solving_prompt)
            return result
            
        except Exception as e:
            return {"success": False, "error": f"Text CAPTCHA solving failed: {str(e)}"}

    async def _solve_math_captcha(self, challenge_text: str) -> Dict[str, Any]:
        """Solve mathematical CAPTCHA"""
        
        math_prompt = f"""
        Solve this mathematical expression:
        
        Expression: {challenge_text}
        
        Extract the mathematical expression and calculate the result.
        Handle common formats:
        - "5 + 3 = ?" -> 8
        - "What is 12 - 4?" -> 8
        - "7 * 2 =" -> 14
        - "15 / 3 =" -> 5
        - "2 + 3 * 4 =" -> 14 (following order of operations)
        
        Return JSON:
        {{
            "success": true/false,
            "answer": numeric_result,
            "expression": "extracted_expression",
            "calculation_steps": ["step1", "step2"],
            "confidence": 0.95
        }}
        """
        
        try:
            result = await self.ai_analyzer._query_ai(math_prompt)
            return result
            
        except Exception as e:
            return {"success": False, "error": f"Math CAPTCHA solving failed: {str(e)}"}

    async def solve_captcha_challenge(self, page: Page, html_content: str) -> Dict[str, Any]:
        """Main method to detect and solve CAPTCHA challenges"""
        
        # Detect CAPTCHA
        detection_result = await self.detect_captcha(page, html_content)
        
        if not detection_result.get("captcha_detected"):
            return {"success": True, "captcha_present": False}
        
        captcha_elements = detection_result.get("captcha_elements", [])
        
        if not captcha_elements:
            return {"success": False, "error": "CAPTCHA detected but no elements found"}
        
        # Handle each CAPTCHA element
        for captcha_element in captcha_elements:
            captcha_type = captcha_element.get("type")
            
            print(f"🔧 Attempting to solve {captcha_type}...")
            
            if captcha_type == "recaptcha_v2":
                result = await self.handle_recaptcha_v2(page, captcha_element)
            elif captcha_type == "recaptcha_v3":
                result = await self.handle_recaptcha_v3(page, captcha_element)
            elif captcha_type == "hcaptcha":
                result = await self.handle_hcaptcha(page, captcha_element)
            elif captcha_type == "image_captcha":
                result = await self.handle_image_captcha(page, captcha_element)
            elif captcha_type == "text_captcha":
                result = await self.handle_text_captcha(page, captcha_element)
            elif captcha_type == "math_captcha":
                result = await self.handle_math_captcha(page, captcha_element)
            else:
                result = {"success": False, "error": f"Unsupported CAPTCHA type: {captcha_type}"}
            
            if result.get("success"):
                print(f"✅ {captcha_type} solved successfully!")
                return {
                    "success": True,
                    "captcha_type": captcha_type,
                    "method": result.get("method"),
                    "captcha_present": True
                }
            else:
                print(f"❌ Failed to solve {captcha_type}: {result.get('error')}")
        
        return {
            "success": False,
            "error": "All CAPTCHA solving attempts failed",
            "captcha_present": True,
            "captcha_types": [elem.get("type") for elem in captcha_elements]
        }