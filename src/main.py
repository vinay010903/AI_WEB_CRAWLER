import asyncio
from playwright.async_api import async_playwright
import json
import os
from dotenv import load_dotenv
from test_extract_selector import extract_all_selectors
import httpx
from utilities_local_ai import local_ai_selector_categorizer 
import pathlib

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def get_create_grouped_selectors(html_content, simple_all_selectors_path, categorized_selectors_path, grouped_selectors_path):
    path_grouped_selectors = pathlib.Path(grouped_selectors_path)
    path_categorized_selectors = pathlib.Path(categorized_selectors_path)
    simple_all_selectors = pathlib.Path(simple_all_selectors_path)

    if path_grouped_selectors.is_file():
        with open(grouped_selectors_path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    elif path_categorized_selectors.is_file() and simple_all_selectors.is_file():
        with open(simple_all_selectors_path, "r", encoding="utf-8") as f:
            simple_selectors = json.load(f)
        with open(categorized_selectors_path, "r", encoding="utf-8") as f:
            categorized_selectors = json.load(f)
        return group_selectors_by_category(simple_selectors, categorized_selectors, grouped_selectors_path)
    
    elif simple_all_selectors.is_file():
        with open(simple_all_selectors_path, "r", encoding="utf-8") as f:
            simple_selectors = json.load(f)
        categorized_selectors = local_ai_selector_categorizer(simple_selectors, "qwen/qwen3-4b-2507")
        with open(categorized_selectors_path, "w", encoding="utf-8") as f:
            json.dump(categorized_selectors, f, indent=2)
        return group_selectors_by_category(simple_selectors, categorized_selectors, grouped_selectors_path)
    
    elif html_content:
        simple_selectors = extract_all_selectors(html_content, None)
        os.makedirs("extracted_data/selectors", exist_ok=True)
        with open(simple_all_selectors_path, 'w') as f:
            json.dump(simple_selectors, f, indent=2)

        categorized_selectors = local_ai_selector_categorizer(simple_selectors, "qwen/qwen3-4b-2507")
        os.makedirs("extracted_data/categorized_selectors", exist_ok=True)
        with open(categorized_selectors_path, 'w') as f:
            json.dump(categorized_selectors, f, indent=2)

        return group_selectors_by_category(simple_selectors, categorized_selectors, grouped_selectors_path)
    
    return {}

async def ask_local_ai_for_specific_selectors(category_selectors, request_type="sign_in", model_name="openai/gpt-oss-20b"):
    batch_size = 25
    total_selectors = len(category_selectors)
    
    for batch_start in range(0, total_selectors, batch_size):
        batch_end = min(batch_start + batch_size, total_selectors)
        current_batch = category_selectors[batch_start:batch_end]
        
        selectors_list = []
        for sel in current_batch:
            if sel.get('selector'):
                selector_entry = {
                    "selector": sel['selector'],
                    "tag": sel.get('tag', ''),
                    "text": sel.get('text_content', '')[:200]
                }
                
                selector_type = sel.get('selector_type', '')
                if 'input' in selector_type and sel.get('input_type'):
                    selector_entry['input_type'] = sel.get('input_type')
                if sel.get('name'):
                    selector_entry['name'] = sel.get('name')
                if 'button' in selector_type and sel.get('button_text'):
                    selector_entry['button_text'] = sel.get('button_text')[:50]
                if sel.get('href'):
                    selector_entry['href'] = sel.get('href')[:50]
                    
                selectors_list.append(selector_entry)
        
        if not selectors_list:
            continue
        
        selectors_json = json.dumps(selectors_list, indent=2)
        
        prompts = {
            "sign_in": f"""Find the BEST selector for clicking "Sign In" or "Login".
            SELECTORS: {selectors_json}
            Return JSON: {{"sign_in_selector": "exact_selector_string"}}""",
            "username": f"""Find the BEST selector for the username/email input field.
            SELECTORS: {selectors_json}
            Return JSON: {{"username_selector": "exact_selector_string"}}""",
            "password": f"""Find the BEST selector for the password input field.
            SELECTORS: {selectors_json}
            Return JSON: {{"password_selector": "exact_selector_string"}}""",
            "submit_button": f"""Find the BEST selector for the submit/continue button.
            SELECTORS: {selectors_json}
            Return JSON: {{"submit_button_selector": "exact_selector_string"}}""",
            "search": f"""Find the BEST selector for the search input field or search box.
            SELECTORS: {selectors_json}
            Return JSON: {{"search_selector": "exact_selector_string"}}"""
        }
        
        prompt = prompts.get(request_type, prompts["sign_in"])
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as http_client:
                payload = {
                    "model": model_name,
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that analyzes web selectors and returns JSON responses."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 4000,
                }
                response = await http_client.post("http://localhost:1234/v1/chat/completions", json=payload)
                result = response.json()["choices"][0]["message"]["content"]
                
                if result.startswith("```json"):
                    result = result[7:]
                if result.endswith("```"):
                    result = result[:-3]
                
                try:
                    ai_response = json.loads(result)
                    if isinstance(ai_response, dict) and len(ai_response) == 1:
                        key, value = next(iter(ai_response.items()))
                        if key and key.lower() not in ["none", "null"] and value and value.lower() not in ["none", "null"]:
                            return ai_response
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass
    
    return {}

def group_selectors_by_category(extracted_selectors, categorized_selectors, output_file_path=None):
    uuid_lookup = {}
    
    selector_types = ['id_selectors', 'class_selectors', 'name_selectors', 'type_selectors',
                     'attribute_selectors', 'input_selectors', 'button_selectors', 
                     'link_selectors', 'form_selectors']
    
    for selector_type in selector_types:
        if selector_type in extracted_selectors:
            for selector_item in extracted_selectors[selector_type]:
                if isinstance(selector_item, dict) and 'uuid' in selector_item:
                    uuid_lookup[selector_item['uuid']] = {
                        'selector_type': selector_type,
                        'data': selector_item
                    }
    
    grouped_by_category = {}
    
    for categorized_item in categorized_selectors:
        if isinstance(categorized_item, dict) and 'uuid' in categorized_item:
            uuid = categorized_item['uuid']
            category = categorized_item.get('category', 'uncategorized')
            confidence = categorized_item.get('confidence', 0.0)
            
            if uuid in uuid_lookup:
                extracted_data = uuid_lookup[uuid]['data']
                selector_type = uuid_lookup[uuid]['selector_type']
                
                enriched_selector = {
                    'uuid': uuid,
                    'confidence': confidence,
                    'selector': extracted_data.get('selector', 'N/A'),
                    'tag': extracted_data.get('tag', 'N/A'),
                    'text_content': extracted_data.get('text_content', extracted_data.get('text', ''))[:200],
                    'selector_type': selector_type,
                    'original_extracted_data': extracted_data
                }
                
                if selector_type == 'input_selectors':
                    enriched_selector['input_type'] = extracted_data.get('type', '')
                    enriched_selector['name'] = extracted_data.get('name', '')
                    enriched_selector['placeholder'] = extracted_data.get('placeholder', '')
                    enriched_selector['selectors'] = extracted_data.get('selectors', [])
                elif selector_type == 'button_selectors':
                    enriched_selector['button_type'] = extracted_data.get('type', '')
                    enriched_selector['button_text'] = extracted_data.get('text', '')
                    enriched_selector['selectors'] = extracted_data.get('selectors', [])
                elif selector_type == 'link_selectors':
                    enriched_selector['href'] = extracted_data.get('href', '')
                elif selector_type == 'attribute_selectors':
                    enriched_selector['attribute'] = extracted_data.get('attribute', '')
                    enriched_selector['value'] = extracted_data.get('value', '')
                
                if category not in grouped_by_category:
                    grouped_by_category[category] = []
                
                grouped_by_category[category].append(enriched_selector)
    
    if output_file_path:
        try:
            os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(grouped_by_category, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    return grouped_by_category

async def run_ai_pipeline_navigator(model_name=None):
    url = "https://www.amazon.in"
    username = os.getenv("AMAZON_USERNAME")
    password = os.getenv("AMAZON_PASSWORD")
    
    if model_name is None:
        model_name = os.getenv("LOCAL_AI_MODEL", "openai/gpt-oss-20b")
    
    print(f"🚀 Starting AI Pipeline Navigator")
    print(f"🌐 Target URL: {url}")
    print(f"🤖 AI Model: {model_name}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        page = await browser.new_page()
        page.set_default_timeout(15000)
        
        loop = asyncio.get_running_loop()
        try:
            print("📱 Step 1: Navigating to Amazon homepage")
            await page.goto(url)
            print("✅ Homepage loaded successfully")
            await asyncio.sleep(2)
            
            print("🔍 Step 2: Extracting and categorizing homepage selectors")
            html_content = await page.content()
            os.makedirs("extracted_data/selectors", exist_ok=True)
            home_selectors_file = "extracted_data/selectors/home_all_selectors.json"
            home_categorized_file = "extracted_data/categorized_selectors/home_categorized.json"
            grouped_selectors_file = "extracted_data/grouped_selectors/home_grouped.json"

            grouped_selectors = await loop.run_in_executor(None, get_create_grouped_selectors, html_content, home_selectors_file, home_categorized_file, grouped_selectors_file)
            print("✅ Homepage selectors extracted and categorized")
            
            print("🔐 Step 3: Finding authentication selectors")
            auth_selectors = grouped_selectors.get('authentication_account', [])
            if not auth_selectors:
                print("❌ No authentication selectors found")
                await browser.close()
                return
            
            print(f"🤖 Found {len(auth_selectors)} authentication selectors, asking AI for sign-in")
            ai_response = await ask_local_ai_for_specific_selectors(auth_selectors, "sign_in", model_name)
            sign_in_selector = ai_response.get('sign_in_selector')
            if not sign_in_selector:
                print("❌ AI could not find sign-in selector")
                await browser.close()
                return
            
            print(f"🔗 Step 4: Clicking sign-in button: {sign_in_selector}")
            try:
                await page.click(sign_in_selector)
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                print("✅ Sign-in clicked successfully")
            except Exception as e:
                print(f"❌ Failed to click sign-in: {e}")
                await browser.close()
                return
            
            print("📋 Step 5: Processing login page")
            await asyncio.sleep(2)
            html_content = await page.content()
            login_selectors_file = "extracted_data/selectors/login_all_selectors.json"
            login_categorized_file = "extracted_data/categorized_selectors/login_categorized.json"
            login_grouped_file = "extracted_data/grouped_selectors/login_grouped.json"
            login_grouped_selectors = await loop.run_in_executor(None, get_create_grouped_selectors, html_content, login_selectors_file, login_categorized_file, login_grouped_file)
            print("✅ Login page selectors processed")

            login_auth_selectors = login_grouped_selectors.get('authentication_account', [])
            print(f"🔍 Found {len(login_auth_selectors)} login authentication selectors")
            
            print("👤 Step 6: Finding and filling username field")
            ai_response = await ask_local_ai_for_specific_selectors(login_auth_selectors, "username", model_name)
            username_selector = ai_response.get('username_selector')
            if not username_selector:
                print("❌ AI could not find username selector")
                await browser.close()
                return
            
            try:
                await page.fill(username_selector, username)
                print(f"✅ Username filled: {username_selector}")
            except Exception as e:
                print(f"❌ Failed to fill username: {e}")
                await browser.close()
                return
            
            print("➡️ Step 7: Finding and clicking continue button")
            ai_response = await ask_local_ai_for_specific_selectors(login_auth_selectors, "submit_button", model_name)
            continue_selector = ai_response.get('submit_button_selector')
            if not continue_selector:
                print("❌ AI could not find continue button")
                await browser.close()
                return
            
            try:
                await page.click(continue_selector)
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                print(f"✅ Continue button clicked: {continue_selector}")
            except Exception as e:
                print(f"❌ Failed to click continue: {e}")
                await browser.close()
                return
            
            print("🔐 Step 8: Processing password page")
            await asyncio.sleep(2)
            html_content = await page.content()
            password_selectors_file = "extracted_data/selectors/password_all_selectors.json"
            password_categorized_file = "extracted_data/categorized_selectors/password_categorized.json"
            password_grouped_file = "extracted_data/grouped_selectors/password_grouped.json"
            password_grouped_selectors = await loop.run_in_executor(None, get_create_grouped_selectors, html_content, password_selectors_file, password_categorized_file, password_grouped_file)
            print("✅ Password page selectors processed")

            password_auth_selectors = password_grouped_selectors.get('authentication_account', [])
            print(f"🔍 Found {len(password_auth_selectors)} password authentication selectors")
            
            print("🔑 Step 9: Finding and filling password field")
            ai_response = await ask_local_ai_for_specific_selectors(password_auth_selectors, "password", model_name)
            password_field_selector = ai_response.get('password_selector')
            if not password_field_selector:
                print("❌ AI could not find password selector")
                await browser.close()
                return
            
            try:
                await page.fill(password_field_selector, password)
                print(f"✅ Password filled: {password_field_selector}")
            except Exception as e:
                print(f"❌ Failed to fill password: {e}")
                await browser.close()
                return
            
            print("🚀 Step 10: Finding and clicking submit button")
            ai_response = await ask_local_ai_for_specific_selectors(password_auth_selectors, "submit_button", model_name)
            submit_selector = ai_response.get('submit_button_selector')
            if not submit_selector:
                print("❌ AI could not find submit button")
                await browser.close()
                return
            
            try:
                await page.click(submit_selector)
                await page.wait_for_url("https://www.amazon.in/**", timeout=15000)
                print(f"✅ Login completed successfully: {submit_selector}")
            except Exception as e:
                print(f"❌ Failed to submit login: {e}")
                await browser.close()
                return
            
            print("🏠 Step 11: Processing logged-in homepage")
            await asyncio.sleep(2)
            html_content = await page.content()
            logged_home_selectors_file = "extracted_data/selectors/logged_home_all_selectors.json"
            logged_home_categorized_file = "extracted_data/categorized_selectors/logged_home_categorized.json"
            logged_home_grouped_file = "extracted_data/grouped_selectors/logged_home_grouped.json"
            logged_home_grouped_selectors = await loop.run_in_executor(None, get_create_grouped_selectors, html_content, logged_home_selectors_file, logged_home_categorized_file, logged_home_grouped_file)
            print("✅ Logged-in homepage selectors processed")

            print("🔍 Step 12: Finding search box")
            search_selectors = logged_home_grouped_selectors.get('search_filters', [])
            if not search_selectors:
                search_selectors = logged_home_grouped_selectors.get('input_form', [])
            
            if search_selectors:
                print(f"🤖 Found {len(search_selectors)} search selectors, asking AI")
                ai_response = await ask_local_ai_for_specific_selectors(search_selectors, "search", model_name)
                search_selector = ai_response.get('search_selector')
                if search_selector:
                    try:
                        product_name = os.getenv("PRODUCT_NAME", "sony camera")
                        print(f"🛍️ Step 13: Searching for product: {product_name}")
                        await page.fill(search_selector, product_name)
                        await asyncio.sleep(1)
                        await page.keyboard.press("Enter")
                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                        print(f"✅ Product search completed: {search_selector}")
                    except Exception as e:
                        print(f"❌ Failed to search for product: {e}")
                else:
                    print("❌ AI could not find search selector")
            else:
                print("❌ No search selectors found")
            
            print("📦 Step 14: Processing product search results")
            await asyncio.sleep(2)
            html_content = await page.content()
            products_selectors_file = "extracted_data/selectors/products_all_selectors.json"
            products_categorized_file = "extracted_data/categorized_selectors/products_categorized.json"
            products_grouped_file = "extracted_data/grouped_selectors/products_grouped.json"
            products_grouped_selectors = await loop.run_in_executor(None, get_create_grouped_selectors, html_content, products_selectors_file, products_categorized_file, products_grouped_file)
            print("✅ Product search results selectors processed")
            
            print("🎯 Step 15: Finding and clicking product link")
            product_item_selectors = products_grouped_selectors.get('product_items', [])
            if product_item_selectors:
                print(f"🤖 Found {len(product_item_selectors)} product item selectors, asking AI for link")
                ai_response = await ask_local_ai_for_specific_selectors(product_item_selectors, "link", model_name)
                product_link_selector = ai_response.get('link_selector')
                if product_link_selector:
                    try:
                        await page.click(product_link_selector)
                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                        print(f"✅ Product link clicked: {product_link_selector}")
                    except Exception as e:
                        print(f"❌ Failed to click product link: {e}")
                else:
                    print("❌ AI could not find product link selector")
            else:
                print("❌ No product item selectors found")

            print("🎉 AI Pipeline Navigation completed successfully!")

        except Exception as e:
            print(f"💥 Pipeline error: {e}")
        finally:
            print("⏳ Waiting before closing browser...")
            await asyncio.sleep(500)
            await browser.close()
            print("🔚 Browser closed")

if __name__ == "__main__":
    asyncio.run(run_ai_pipeline_navigator("qwen/qwen3-4b-2507"))