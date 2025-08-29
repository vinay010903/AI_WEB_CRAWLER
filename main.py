import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from groq import Groq
import json
import time
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key)
async def go_to_login(page, hover_selector, login_selector):
    try:
        if hover_selector and hover_selector.strip().lower() != "none":
            await page.hover(hover_selector)
            print(f"✅ Hovered: {hover_selector}")

        await page.click(login_selector)
        print(f"✅ Clicked: {login_selector}")

        # Option 1: Wait for URL change instead of networkidle
        try:
            await page.wait_for_url("**/ap/signin**", timeout=10000)
            print("✅ Login page loaded (URL changed)")
        except:
            # Option 2: Wait for specific element to appear
            try:
                await page.wait_for_selector('input[name="email"], input[id="ap_email"]', timeout=10000)
                print("✅ Login form detected")
            except:
                # Option 3: Simple wait with load state check
                await page.wait_for_load_state("domcontentloaded", timeout=10000)
                print("✅ Page loaded (DOM ready)")

        redirected_url = page.url
        print(f"🔗 Current URL: {redirected_url}")
        return redirected_url

    except Exception as e:
        print(f"❌ Failed in login click: {e}")
        # Try to get current URL even if wait failed
        try:
            redirected_url = page.url
            print(f"🔗 Current URL (after error): {redirected_url}")
            return redirected_url
        except:
            return None


# ---- Step 2: Extract relevant selectors only ----
async def extract_selectors(page, selector_type="username"):
    # Wait a bit for dynamic content to load
    await asyncio.sleep(2)
    
    content = await page.content()
    soup = BeautifulSoup(content, "html.parser")
    l = soup.prettify()[:1000]
    elements = []
    if selector_type == "username":
        # Focus on input fields and buttons for username page
        relevant_tags = soup.find_all(['input', 'button', 'form', 'div'], 
                                    attrs={'type': True, 'id': True, 'name': True, 'class': True})
    elif selector_type == "password":
        # Focus on password fields and submit buttons
        relevant_tags = soup.find_all(['input', 'button', 'form', 'div'], 
                                    attrs={'type': True, 'id': True, 'name': True, 'class': True})
    elif selector_type == "search":
        # Focus on search elements - input fields and search buttons
        relevant_tags = soup.find_all(['input', 'button', 'form', 'div', 'span'], 
                                    attrs={'type': True, 'id': True, 'name': True, 'class': True, 'value': True})
    elif selector_type == "product":
        # Focus on review and product elements
        relevant_tags = soup.find_all(['div', 'span', 'a', 'p', 'h1', 'h2', 'h3'], 
                                    attrs={'data-hook': True, 'id': True, 'name': True, 'class': True, 'data-component-type': True})
    elif selector_type == "review_link":
        # Focus on elements that might contain links to review pages
        relevant_tags = soup.find_all(['a', 'div', 'span'], 
                                    attrs={'href': True, 'id': True, 'name': True, 'class': True, 'data-hook': True})
    elif selector_type == "review_page":
        # Focus on review page elements
        relevant_tags = soup.find_all(['div', 'span', 'a', 'p', 'h1', 'h2', 'h3', 'img'], 
                                    attrs={'data-hook': True, 'id': True, 'name': True, 'class': True, 'data-component-type': True})
    
    # Filter and limit elements
    for tag in relevant_tags[:50]:  # Limit to first 50 relevant elements
        attrs = []
        for k, v in tag.attrs.items():
            if k in ['type', 'id', 'name', 'class', 'value', 'data-hook', 'data-component-type', 'href']:  # Extended attributes for product pages
                if isinstance(v, list):
                    v = ' '.join(v)
                attrs.append(f'{k}="{v}"')
        
        if attrs:  # Only add if it has relevant attributes
            elements.append(f"<{tag.name} {' '.join(attrs)}>")
    
    return elements, l


# ---- Step 3: Use LLM to pick username/continue selectors ----
def find_username_selectors(elements):
    prompt = f"""
You are given HTML tags from a login page. Identify the best CSS selectors for username field and continue button.

HTML Elements (showing first 30):
{elements[:30]}  # limiting to first 30 elements

IMPORTANT RULES:
1. Only use VALID CSS selectors (no jQuery syntax like :contains())
2. Use attribute selectors like [id="something"], [name="something"], [type="something"]
3. Use class selectors like .class-name
4. Use ID selectors like #element-id
5. For buttons, look for specific IDs, names, or classes, NOT text content
6. Example valid selectors: input[name="email"], #ap_email, input[type="email"], #continue, input[id="continue"]

Look for:
- Username field: input with type="email", name="email", id containing "email", etc.
- Continue button: button or input with id containing "continue", "next", or similar

Output JSON format only:
{{
  "username": ["selector1","selector2"],
  "continue": ["selector1","selector2"]
}}
Don't provide any text except for the JSON. Only use valid CSS selectors.
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        timeout=30
    )
    return response.choices[0].message.content


# ---- Step 5: Use LLM to pick password/submit selectors ----
def find_password_selectors(elements):
    prompt = f"""
You are given HTML tags from a password page. Identify the best CSS selectors for password field and submit button.

HTML Elements (showing first 30):
{elements[:30]}  # limiting to first 30 elements

IMPORTANT RULES:
1. Only use VALID CSS selectors (no jQuery syntax like :contains())
2. Use attribute selectors like [id="something"], [name="something"], [type="something"]
3. Use class selectors like .class-name
4. Use ID selectors like #element-id
5. For buttons, look for specific IDs, names, or classes, NOT text content
6. Example valid selectors: input[type="password"], #ap_password, input[name="password"], #signInSubmit

Look for:
- Password field: input with type="password", name="password", id containing "password", etc.
- Submit button: button or input with id containing "submit", "signin", "login", or similar

CRITICAL: Use EXACTLY these JSON keys - "password" and "submit" (not "Sign in" or any other text)

Output JSON format only:
{{
  "password": ["selector1","selector2"],
  "submit": ["selector1","selector2"]
}}
Don't provide any text except for the JSON. Only use valid CSS selectors and EXACT key names.
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        timeout=30
    )
    return response.choices[0].message.content


# ---- Step 4: Playwright username entry ----
async def perform_username_entry(page, selectors, username):
    # Try multiple username selectors
    username_filled = False
    for selector in selectors.get("username", []):
        try:
            await page.fill(selector, username)
            print(f"✅ Filled username with selector: {selector}")
            username_filled = True
            break
        except Exception as e:
            print(f"❌ Failed username selector {selector}: {e}")
            continue
    
    if not username_filled:
        print("❌ Could not fill username field")
        return False
    
    # Small delay before clicking continue
    await asyncio.sleep(1)
    
    # Try multiple continue selectors
    continue_clicked = False
    for selector in selectors.get("continue", []):
        try:
            await page.click(selector)
            print(f"✅ Clicked continue with selector: {selector}")
            continue_clicked = True
            break
        except Exception as e:
            print(f"❌ Failed continue selector {selector}: {e}")
            continue
    
    if not continue_clicked:
        print("❌ Could not click continue button")
        return False
        
    # Wait for password page to load
    try:
        await page.wait_for_url("**/ap/signin**", timeout=10000)
        print("✅ Password page loaded (URL check)")
    except:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            print("✅ Page transition completed")
        except Exception as e:
            print(f"❌ Failed to wait for password page: {e}")
            return False
    
    return True


# ---- Step 7: Use LLM to pick search selectors ----
def find_search_selectors(elements):
    prompt = f"""
You are given HTML tags from Amazon main page. Identify the best CSS selectors for search box and search button.

HTML Elements (showing first 50):
{elements[:50]}  # showing more elements to help find search button

IMPORTANT RULES:
1. Only use VALID CSS selectors (no jQuery syntax like :contains())
2. Use attribute selectors like [id="something"], [name="something"], [type="something"]
3. Use class selectors like .class-name
4. Use ID selectors like #element-id
5. For buttons, look for specific IDs, names, or classes, NOT text content
6. Example valid selectors: input[name="field-keywords"], #twotabsearchtextbox, input[type="submit"]

Look for:
- Search box: input with name="field-keywords", id containing "search", type="text", etc.
- Search button: Look for ANY of these patterns:
  * input with type="submit" 
  * button elements near search box
  * elements with id containing "search", "submit", "nav-search"
  * elements with class containing "search", "submit", "button"
  * span elements that might wrap search buttons
  * div elements with click handlers for search

CRITICAL: You MUST provide at least 2-3 search button selectors. Look carefully through ALL elements.
CRITICAL: Use EXACTLY these JSON keys - "search_box" and "search_button"

Output JSON format only:
{{
  "search_box": ["selector1","selector2"],
  "search_button": ["selector1","selector2","selector3"]
}}
Don't provide any text except for the JSON. Only use valid CSS selectors and EXACT key names.
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        timeout=30
    )
    return response.choices[0].message.content


# ---- Step 9: Use LLM to pick product link selectors ----
def find_product_selectors(elements):
    prompt = f"""
You are given HTML tags from Amazon search results page. Identify ONLY the 2 BEST CSS selectors for product links.
HTML Elements (showing first 30):
{elements[:30]}

IMPORTANT RULES:
1. Only use VALID CSS selectors (no jQuery syntax)
2. Provide EXACTLY 2 selectors maximum
3. Use simple, effective selectors like: a[href*='/dp/'], [data-component-type="s-search-result"]
4. Focus on main product title links, not sponsored links

CRITICAL: Provide EXACTLY 2 selectors, no more!

Output JSON format only:
{{
  "product_links": ["selector1","selector2"]
}}
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        timeout=30,
        max_tokens=200  # Add token limit
    )
    return response.choices[0].message.content

# ---- NEW: Use LLM to find review page link selectors ----
def find_review_link_selectors(elements):
    prompt = f"""
You are given HTML tags from Amazon product page. Identify the best CSS selectors for links that lead to the reviews page.

HTML Elements (showing first 30):
{elements[:30]}  # limiting to first 30 elements

IMPORTANT RULES:
1. Only use VALID CSS selectors (no jQuery syntax like :contains())
2. Look for links (a tags) that contain text like "See all reviews", "Customer reviews", or have href patterns like "/product-reviews/"
3. Focus on elements that lead to dedicated review pages, not individual reviews on the product page
4. Example valid selectors: a[href*="product-reviews"], a[data-hook="see-all-reviews-link"]

Look for:
- Review page links: a tags with href containing "product-reviews", "customer-reviews", or similar
- Review summary links: elements that lead to review pages when clicked

CRITICAL: Use EXACTLY these JSON keys - "review_page_links"

Output JSON format only:
{{
  "review_page_links": ["selector1","selector2"]
}}
Don't provide any text except for the JSON. Only use valid CSS selectors and EXACT key names.
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        timeout=30
    )
    return response.choices[0].message.content


# ---- MODIFIED: Use LLM to pick review selectors for dedicated review pages ----
def find_review_selectors(elements):
    prompt = f"""
You are given HTML tags from Amazon DEDICATED REVIEWS PAGE. Identify the best CSS selectors for review elements and pagination.

HTML Elements (showing first 30):
{elements[:30]}  # limiting to first 30 elements



IMPORTANT RULES:
1. Only use VALID CSS selectors (no jQuery syntax like :contains())
2. Look for review containers, review text, ratings, reviewer names on a dedicated reviews page
3. Focus on customer review sections with multiple reviews listed
4. Also look for pagination elements like "Next" buttons or page numbers
5. Example selectors: [data-hook="review-body"], [data-hook="review-star-rating"], [class*="review"]

Look for:
- Review containers: divs containing individual reviews (usually with data-hook="review")
- Review text: spans or divs with review content (data-hook="review-body" or similar)
- Review ratings: elements with star ratings (data-hook="review-star-rating")
- Reviewer names: spans with customer names (class*="author" or data-hook*="review-author")
- Review dates: spans with review dates
- Verified purchase: elements indicating verified purchase status
- Next page button: button or link for next page of reviews (usually contains "Next" text or arrow)

"CRITICAL: If you do NOT see the standard data-hook attributes (like 'review', 'review-body', etc.), look for alternative patterns:"
"- Look for divs with classes containing 'review', 'comment', 'testimonial'"
"- Look for spans or divs with class names like 'review-text', 'comment-body'"
"- Look for ratings in 'class' attributes that contain 'star', 'rating', 'a-icon-star'"
"- The structure might be different on this page. Be creative and look for any div that appears to contain a user's review text."

Output JSON format only:
{{
  "review_containers": ["selector1","selector2"],
  "review_text": ["selector1","selector2"],
  "review_ratings": ["selector1","selector2"], 
  "reviewer_names": ["selector1","selector2"],
  "review_dates": ["selector1","selector2"],
  "verified_purchase": ["selector1","selector2"],
  "next_page_button": ["selector1","selector2"]
}}
Don't provide any text except for the JSON. Only use valid CSS selectors and EXACT key names.
"""
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        timeout=30
    )
    return response.choices[0].message.content


# ---- Step 11: Extract product links from search results ----
async def extract_product_links(page, selectors, max_products=5):
    product_links = []
    print("🔍 Debugging product links...")
    # Try multiple product link selectors - ONLY LLM PROVIDED SELECTORS
    for selector in selectors.get("product_links", []):
        try:
            elements = await page.query_selector_all(selector)
            print(f"Found {len(elements)} elements with selector: {selector}")
            for element in elements[:max_products]:  # Limit to max_products
                try:
                    href = await element.get_attribute('href')
                    if href and ('/dp/' in href or '/gp/product/' in href or '/product/' in href):
                        # Make absolute URL if relative
                        if href.startswith('/'):
                            href = f"https://www.amazon.in{href}"
                        
                        # Get product title for reference
                        title = await element.evaluate('el => el.textContent')
                        if title:
                            title = title.strip()[:100]  # Limit title length
                        
                        product_links.append({
                            'url': href,
                            'title': title or 'No title found',
                            'selector_used': selector
                        })
                        print(f"✅ Found product: {title[:50]}...")
                        
                except Exception as e:
                    print(f"❌ Error extracting link: {e}")
                    continue
            
            if product_links:
                break  # Stop after finding products with first working selector
                
        except Exception as e:
            print(f"❌ Failed selector {selector}: {e}")
            continue
    
    print(f"📊 Total products found: {len(product_links)}")
    return product_links


# ---- NEW: Navigate to review page ----
async def navigate_to_review_page(page, selectors):
    """Navigate from product page to dedicated reviews page - ONLY LLM SELECTORS"""
    print("Looking for review page links...")
    
    print("DEBUG: Checking current page URL:", page.url)
    
    review_page_url = None
    
    # Try ONLY LLM provided review link selectors - NO HARDCODED FALLBACKS
    for selector in selectors.get("review_page_links", []):
        try:
            print(f"DEBUG: Trying LLM selector: {selector}")
            elements = await page.query_selector_all(selector)
            print(f"Found {len(elements)} review link elements with selector: {selector}")
            
            for element in elements:
                try:
                    href = await element.get_attribute('href')
                    text = await element.evaluate('el => el.textContent')
                    print(f"DEBUG: Found element - href: '{href}', text: '{text[:30] if text else 'No text'}'")
                    
                    if href and ('product-reviews' in href or 'customer-reviews' in href or '/reviews/' in href or '#customerReviews' in href):
                        # Make absolute URL if relative
                        if href.startswith('/'):
                            href = f"https://www.amazon.in{href}"
                        elif href.startswith('#'):
                            # Handle anchor links
                            href = page.url.split('#')[0] + href
                        
                        review_page_url = href
                        print(f"Found review page URL: {href}")
                        break
                        
                except Exception as e:
                    print(f"Error extracting review link: {e}")
                    continue
            
            if review_page_url:
                break  # Stop after finding first working review link
                
        except Exception as e:
            print(f"Failed review link selector {selector}: {e}")
            continue
    
    if review_page_url:
        try:
            print(f"Navigating to review page: {review_page_url}")
            await page.goto(review_page_url)
            await page.wait_for_load_state("domcontentloaded", timeout=15000)
            
            # Wait for reviews to load
            await asyncio.sleep(3)
            
            # Check if we successfully reached a review page
            final_url = page.url
            print(f"Successfully navigated to: {final_url}")
            
            return True
        except Exception as e:
            print(f"Failed to navigate to review page: {e}")
            return False
    else:
        print("Could not find review page URL using LLM selectors")
        return False


# ---- NEW: Navigate to next page of reviews ----
async def navigate_to_next_page(page, selectors):
    """Navigate to next page of reviews - ONLY LLM SELECTORS"""
    print("🔄 Looking for next page button...")
    # Try ONLY LLM provided next page selectors - NO HARDCODED FALLBACKS
    for selector in selectors.get("next_page_button", []):
        try:
            next_button = await page.query_selector(selector)
            if next_button:
                # Check if the button is enabled (not disabled)
                is_disabled = await next_button.evaluate('el => el.disabled || el.classList.contains("a-disabled") || el.getAttribute("aria-disabled") === "true"')
                
                if not is_disabled:
                    print(f"✅ Found enabled next button with selector: {selector}")
                    await next_button.click()
                    
                    # Wait for new page to load
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                        # Additional wait for dynamic content
                        await asyncio.sleep(2)
                        print("✅ Successfully navigated to next page")
                        return True
                    except Exception as e:
                        print(f"❌ Failed to wait for next page load: {e}")
                        return False
                else:
                    print(f"⏭️ Next button found but disabled (last page): {selector}")
                    return False
                    
        except Exception as e:
            print(f"❌ Failed next button selector {selector}: {e}")
            continue
    
    print("❌ No next page button found using LLM selectors")
    return False


# ---- MODIFIED: Extract reviews from all pages ----
async def extract_all_reviews(page, selectors, max_reviews_per_page=20, max_pages=10):
    """Extract reviews from multiple pages with pagination - ONLY LLM SELECTORS"""
    all_reviews = []
    current_page = 1
    print(f"🔍 Starting review extraction with pagination (max {max_pages} pages)...")
    while current_page <= max_pages:
        print(f"\n📄 Extracting reviews from page {current_page}...")
        # Extract reviews from current page
        page_reviews = await extract_reviews_from_current_page(page, selectors, max_reviews_per_page)
        if page_reviews:
            # Add page number to each review
            for review in page_reviews:
                review['page_number'] = current_page
            all_reviews.extend(page_reviews)
            print(f"✅ Extracted {len(page_reviews)} reviews from page {current_page}")
            print(f"📊 Total reviews so far: {len(all_reviews)}")
        else:
            print(f"❌ No reviews found on page {current_page}")
            break
        
        # Try to navigate to next page
        if current_page < max_pages:
            print(f"🔄 Attempting to navigate to page {current_page + 1}...")
            next_page_success = await navigate_to_next_page(page, selectors)
            
            if next_page_success:
                current_page += 1
                # Wait a bit more for the page to fully load
                await asyncio.sleep(2)
            else:
                print(f"⏹️ No more pages available or reached last page. Stopping at page {current_page}")
                break
        else:
            print(f"⏹️ Reached maximum pages limit ({max_pages})")
            break
    
    print(f"🎉 Completed pagination. Total reviews extracted: {len(all_reviews)} from {current_page} pages")
    return all_reviews


# ---- COMPLETELY REWRITTEN: Extract reviews from current page ONLY using LLM selectors ----
async def extract_reviews_from_current_page(page, selectors, max_reviews=20):
    """Extract reviews from the current page ONLY using LLM provided selectors - NO HARDCODED FALLBACKS"""
    reviews = []
    
    print("DEBUG: Starting review extraction from current page using ONLY LLM selectors...")
    print("DEBUG: Current page URL:", page.url)
    
    # Wait for reviews to load
    await asyncio.sleep(3)
    
    # Try to find review containers first using ONLY LLM selectors
    review_containers = []
    for selector in selectors.get("review_containers", []):
        try:
            print(f"DEBUG: Trying LLM review container selector: {selector}")
            elements = await page.query_selector_all(selector)
            print(f"DEBUG: Found {len(elements)} review containers with selector: {selector}")
            if elements:
                review_containers = elements[:max_reviews]
                print(f"Using {len(review_containers)} review containers from LLM selector: {selector}")
                break
        except Exception as e:
            print(f"Failed LLM review container selector {selector}: {e}")
            continue
    
    if not review_containers:
        print("No review containers found using LLM selectors, trying individual review text selectors...")
        # Try ONLY LLM provided review text selectors - NO HARDCODED FALLBACKS
        for selector in selectors.get("review_text", []):
            try:
                print(f"DEBUG: Trying LLM review text selector: {selector}")
                elements = await page.query_selector_all(selector)
                print(f"DEBUG: Found {len(elements)} elements with LLM selector: {selector}")
                if elements:
                    for i, element in enumerate(elements[:max_reviews]):
                        try:
                            review_text = await element.evaluate('el => el.textContent')
                            if review_text and len(review_text.strip()) > 10:
                                reviews.append({
                                    'review_text': review_text.strip(),
                                    'reviewer_name': 'Unknown',
                                    'rating': 'Unknown',
                                    'review_date': 'Unknown',
                                    'verified_purchase': 'Unknown',
                                    'review_index': i + 1,
                                    'page_number': 1,
                                    'extraction_method': 'llm_direct_text_selector'
                                })
                                print(f"Extracted review {i + 1} using LLM text selector: {review_text[:50]}...")
                        except Exception as e:
                            print(f"Error extracting text from LLM selector element {i}: {e}")
                            continue
                    if reviews:
                        break
            except Exception as e:
                print(f"Failed LLM review text selector {selector}: {e}")
                continue
    else:
        # Extract from review containers using ONLY LLM selectors
        print(f"Extracting from {len(review_containers)} review containers using LLM selectors...")
        for i, container in enumerate(review_containers):
            try:
                review_data = {
                    'review_text': 'Not found',
                    'reviewer_name': 'Unknown',
                    'rating': 'Unknown',
                    'review_date': 'Unknown',
                    'verified_purchase': 'Unknown',
                    'review_index': i + 1,
                    'page_number': 1,
                    'extraction_method': 'llm_container_based'
                }
                
                # Extract review text using ONLY LLM selectors
                for text_selector in selectors.get("review_text", []):
                    try:
                        text_element = await container.query_selector(text_selector)
                        if text_element:
                            review_text = await text_element.evaluate('el => el.textContent')
                            if review_text:
                                review_data['review_text'] = review_text.strip()
                                print(f"Found review text using LLM selector '{text_selector}': {review_text[:50]}...")
                                break
                    except Exception as e:
                        print(f"Error with LLM text selector '{text_selector}': {e}")
                        continue
                
                # Extract reviewer name using ONLY LLM selectors
                for name_selector in selectors.get("reviewer_names", []):
                    try:
                        name_element = await container.query_selector(name_selector)
                        if name_element:
                            reviewer_name = await name_element.evaluate('el => el.textContent')
                            if reviewer_name:
                                review_data['reviewer_name'] = reviewer_name.strip()
                                break
                    except:
                        continue
                
                # Extract rating using ONLY LLM selectors
                for rating_selector in selectors.get("review_ratings", []):
                    try:
                        rating_element = await container.query_selector(rating_selector)
                        if rating_element:
                            # Try to get rating from class name or text content
                            rating_class = await rating_element.get_attribute('class')
                            if rating_class and 'star' in rating_class:
                                # Extract star rating from class name
                                import re
                                star_match = re.search(r'(\d+(?:\.\d+)?)', rating_class)
                                if star_match:
                                    review_data['rating'] = star_match.group(1)
                                else:
                                    rating_text = await rating_element.evaluate('el => el.textContent')
                                    if rating_text:
                                        review_data['rating'] = rating_text.strip()
                            else:
                                rating_text = await rating_element.evaluate('el => el.textContent')
                                if rating_text:
                                    review_data['rating'] = rating_text.strip()
                            break
                    except:
                        continue
                
                # Extract review date using ONLY LLM selectors
                for date_selector in selectors.get("review_dates", []):
                    try:
                        date_element = await container.query_selector(date_selector)
                        if date_element:
                            review_date = await date_element.evaluate('el => el.textContent')
                            if review_date:
                                review_data['review_date'] = review_date.strip()
                                break
                    except:
                        continue
                
                # Extract verified purchase status using ONLY LLM selectors
                for verified_selector in selectors.get("verified_purchase", []):
                    try:
                        verified_element = await container.query_selector(verified_selector)
                        if verified_element:
                            verified_text = await verified_element.evaluate('el => el.textContent')
                            if verified_text:
                                review_data['verified_purchase'] = 'Yes' if 'verified' in verified_text.lower() else 'No'
                                break
                    except:
                        continue
                
                if review_data['review_text'] != 'Not found' and len(review_data['review_text']) > 10:
                    reviews.append(review_data)
                    print(f"Extracted review {i + 1}: {review_data['review_text'][:50]}...")
                    
            except Exception as e:
                print(f"Error extracting review {i + 1}: {e}")
                continue
    
    print(f"Reviews extracted from current page using LLM selectors: {len(reviews)}")
    if len(reviews) == 0:
        print("No reviews extracted using LLM selectors! This indicates:")
        print("1. LLM provided incorrect selectors")
        print("2. Page structure different than expected")
        print("3. Reviews might be in a different location")
        print("4. Page not loaded properly")
        
        # Save page source for debugging
        try:
            content = await page.content()
            with open("debug_review_page.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("Saved page source to debug_review_page.html for inspection")
        except:
            pass
    
    return reviews


# ---- MODIFIED: Process multiple products and extract reviews from review pages ----
async def process_products_and_reviews(page, product_links, max_products=3):
    final_results = {
        'search_query': '',
        'total_products_found': len(product_links),
        'products_processed': 0,
        'products': []
    }
    
    for i, product in enumerate(product_links[:max_products]):
        print(f"\n🛍️ Processing product {i + 1}/{min(max_products, len(product_links))}: {product['title'][:50]}...")
        try:
            # Navigate to product page
            await page.goto(product['url'])
            await page.wait_for_load_state("domcontentloaded", timeout=10000)

            # Extract selectors from product page for finding review links
            print("📊 Extracting product page selectors for review links...")
            elements_product, l_product = await extract_selectors(page, "review_link")
            
            # Save product page elements for debugging
            os.makedirs("selectors2", exist_ok=True)
            file_path_product = f"selectors2/product_{i + 1}_review_link_selectors.txt"
            with open(file_path_product, "w", encoding="utf-8") as f:
                for element in elements_product:
                    f.write(element + "\n")
            
            # Get LLM recommendations for review page links
            print("🤖 Getting LLM recommendations for review page links...")
            temp_review_link_selectors = find_review_link_selectors(elements_product)
            print(f"Review Link LLM Response: {temp_review_link_selectors}")
            
            # Parse LLM response for review links
            review_link_selectors = json.loads(temp_review_link_selectors)
            
            # Navigate to review page
            print("🔗 Navigating to dedicated review page...")
            navigation_success = await navigate_to_review_page(page, review_link_selectors)
            
            if navigation_success:
                # Extract selectors from review page
                print("📊 Extracting review page selectors...")
                elements_review_page, l_review_page = await extract_selectors(page, "review_page")
                
                # Save review page elements for debugging
                file_path_review_page = f"selectors2/product_{i + 1}_review_page_selectors.txt"
                with open(file_path_review_page, "w", encoding="utf-8") as f:
                    for element in elements_review_page:
                        f.write(element + "\n")
                
                # Get LLM recommendations for reviews
                print("🤖 Getting LLM recommendations for review extraction...")
                temp_review_selectors = find_review_selectors(elements_review_page)
                print(f"Review LLM Response: {temp_review_selectors}")
                
                # Parse LLM response for reviews
                review_selectors = json.loads(temp_review_selectors)
                
                # Extract reviews from review page with pagination
                print("📝 Extracting reviews from dedicated review page with pagination...")
                reviews = await extract_all_reviews(page, review_selectors, max_reviews_per_page=20, max_pages=10)
                
                # Add to final results
                product_result = {
                    'product_index': i + 1,
                    'product_title': product['title'],
                    'product_url': product['url'],
                    'review_page_url': page.url,
                    'reviews_found': len(reviews),
                    'reviews': reviews
                }
                
                final_results['products'].append(product_result)
                final_results['products_processed'] += 1
                
                print(f"✅ Completed product {i + 1}: Found {len(reviews)} reviews from review page")
            
            else:
                print(f"❌ Could not navigate to review page for product {i + 1}")
                # Add error entry
                final_results['products'].append({
                    'product_index': i + 1,
                    'product_title': product['title'],
                    'product_url': product['url'],
                    'error': 'Could not navigate to review page',
                    'reviews_found': 0,
                    'reviews': []
                })
            
        except Exception as e:
            print(f"❌ Error processing product {i + 1}: {e}")
            # Add error entry
            final_results['products'].append({
                'product_index': i + 1,
                'product_title': product['title'],
                'product_url': product['url'],
                'error': str(e),
                'reviews_found': 0,
                'reviews': []
            })
            continue
    
    return final_results


async def perform_product_search(page, selectors, product_query):
    # Try multiple search box selectors
    search_filled = False
    for selector in selectors.get("search_box", []):
        try:
            await page.fill(selector, product_query)
            print(f"✅ Filled search box with selector: {selector}")
            search_filled = True
            break
        except Exception as e:
            print(f"❌ Failed search box selector {selector}: {e}")
            continue
    
    if not search_filled:
        print("❌ Could not fill search box")
        return False
    
    # Small delay before clicking search
    await asyncio.sleep(1)
    
    # Try multiple search button selectors - ONLY LLM PROVIDED SELECTORS
    search_clicked = False
    for selector in selectors.get("search_button", []):
        try:
            await page.click(selector)
            print(f"✅ Clicked search button with selector: {selector}")
            search_clicked = True
            break
        except Exception as e:
            print(f"❌ Failed search button selector {selector}: {e}")
            continue
    
    if not search_clicked:
        print("❌ Could not click search button using LLM selectors")
        return False
        
    # Wait for search results to load
    try:
        await page.wait_for_url("**/s?**", timeout=15000)
        print("✅ Search successful - reached search results page")
    except:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            print("✅ Search submitted - page loaded")
        except Exception as e:
            print(f"❌ Failed to wait for search results: {e}")
            return False
    
    return True


async def perform_password_entry(page, selectors, password):
    # Try multiple password selectors
    password_filled = False
    for selector in selectors.get("password", []):
        try:
            await page.fill(selector, password)
            print(f"✅ Filled password with selector: {selector}")
            password_filled = True
            break
        except Exception as e:
            print(f"❌ Failed password selector {selector}: {e}")
            continue
    

    if not password_filled:
        print("❌ Could not fill password field")
        return False
    

    # Small delay before clicking submit
    await asyncio.sleep(1)
    # Try multiple submit selectors - ONLY LLM PROVIDED SELECTORS
    submit_clicked = False
    for selector in selectors.get("submit", []):
        try:
            await page.click(selector)
            print(f"✅ Clicked submit with selector: {selector}")
            submit_clicked = True
            break
        except Exception as e:
            print(f"❌ Failed submit selector {selector}: {e}")
            continue
    
    if not submit_clicked:
        print("❌ Could not click submit button using LLM selectors")
        return False
        
    
    # Wait for login completion (redirect to main page or dashboard)
    try:
        await page.wait_for_url("https://www.amazon.in/**", timeout=15000)
        print("✅ Login successful - redirected to Amazon main page")
    except:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=10000)
            print("✅ Login form submitted - page loaded")
        except Exception as e:
            print(f"❌ Failed to wait for login completion: {e}")
            return False
    
    return True


# ---- Main Pipeline ----
async def run_pipeline():
    with open("selectors/final2.json", "r") as f:
        selectors = json.load(f)
    hover_selector = selectors[0].get("hover_selector")
    login_selector = selectors[0].get("login_selector")
    url = "https://www.amazon.in"
    username = os.getenv("AMAZON_USERNAME")
    password = os.getenv("AMAZON_PASSWORD")
    search_product = "polo Tshirt" 
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=1000)  
        page = await browser.new_page()
        # Set longer timeout
        page.set_default_timeout(15000)
        
        await page.goto(url)
        print("✅ Loaded Amazon homepage")

        # Step 1: go to login
        redirected_url = await go_to_login(page, hover_selector, login_selector)
        if not redirected_url:
            print("❌ Could not navigate to login page")
            await browser.close()
            return
        print("📊 Extracting username page selectors...")
        elements, l = await extract_selectors(page, "username")
        # Create directories if they don't exist
        os.makedirs("selectors2", exist_ok=True)
        os.makedirs("selectors", exist_ok=True)
        # Save username page elements
        file_path1 = "selectors2/stage1_username_selectors.txt"
        with open(file_path1, "w", encoding="utf-8") as f:
            for element in elements:
                f.write(element + "\n")
        
        file_path_temp = "selectors2/username_page.html"
        with open(file_path_temp, "w", encoding="utf-8") as f:
            f.write(l)

        # Step 3: let LLM choose username page selectors
        print("🤖 Getting LLM recommendations for username page...")
        temp_selectors = find_username_selectors(elements)
        print(f"Username LLM Response: {temp_selectors}")

        # Parse LLM response for username page
        username_selectors = json.loads(temp_selectors)

        file_path2 = "selectors/stage2_username_selectors.json"
        with open(file_path2, "w", encoding="utf-8") as f:
            json.dump(username_selectors, f, indent=4)

        # Step 4: perform username entry
        print("🔐 Entering username...")
        username_success = await perform_username_entry(page, username_selectors, username)
        if not username_success:
            print("❌ Username entry failed")
            await browser.close()
            return

        # Step 5: extract selectors from password page
        print("📊 Extracting password page selectors...")
        elements_pwd, l_pwd = await extract_selectors(page, "password")
        
        # Save password page elements
        file_path3 = "selectors2/stage1_password_selectors.txt"
        with open(file_path3, "w", encoding="utf-8") as f:
            for element in elements_pwd:
                f.write(element + "\n")
        
        file_path_temp_pwd = "selectors2/password_page.html"
        with open(file_path_temp_pwd, "w", encoding="utf-8") as f:
            f.write(l_pwd)

        # Step 6: let LLM choose password page selectors
        print("🤖 Getting LLM recommendations for password page...")
        temp_pwd_selectors = find_password_selectors(elements_pwd)
        print(f"Password LLM Response: {temp_pwd_selectors}")

        # Parse LLM response for password page
        password_selectors = json.loads(temp_pwd_selectors)

        file_path4 = "selectors/stage2_password_selectors.json"
        with open(file_path4, "w", encoding="utf-8") as f:
            json.dump(password_selectors, f, indent=4)

        # Step 7: perform password entry and submit
        print("🔐 Entering password and submitting...")
        password_success = await perform_password_entry(page, password_selectors, password)
        
        if password_success:
            print("🎉 Login completed successfully!")
        else:
            print("❌ Password entry/submit failed")
            await browser.close()
            return

        # Step 8: Extract selectors from main page for search
        print("📊 Extracting main page search selectors...")
        elements_search, l_search = await extract_selectors(page, "search")
        
        # Save main page search elements
        file_path5 = "selectors2/stage1_search_selectors.txt"
        with open(file_path5, "w", encoding="utf-8") as f:
            for element in elements_search:
                f.write(element + "\n")
        
        file_path_temp_search = "selectors2/main_page.html"
        with open(file_path_temp_search, "w", encoding="utf-8") as f:
            f.write(l_search)

        # Step 9: Let LLM choose search selectors
        print("🤖 Getting LLM recommendations for search functionality...")
        temp_search_selectors = find_search_selectors(elements_search)
        print(f"Search LLM Response: {temp_search_selectors}")

        # Parse LLM response for search
        search_selectors = json.loads(temp_search_selectors)

        file_path6 = "selectors/stage2_search_selectors.json"
        with open(file_path6, "w", encoding="utf-8") as f:
            json.dump(search_selectors, f, indent=4)

        # Step 10: Perform product search
        print(f"🔍 Searching for product: '{search_product}'...")
        search_success = await perform_product_search(page, search_selectors, search_product)
        
        if search_success:
            print("🎉 Product search completed successfully!")
            print(f"🔗 Current URL: {page.url}")
            
            # Step 11: Extract product links from search results
            print("📊 Extracting product links from search results...")
            elements_results, l_results = await extract_selectors(page, "search")
            
            # Save search results elements
            file_path7 = "selectors2/stage1_results_selectors.txt"
            with open(file_path7, "w", encoding="utf-8") as f:
                for element in elements_results:
                    f.write(element + "\n")
            
            # Get LLM recommendations for product links
            print("🤖 Getting LLM recommendations for product links...")
            temp_product_selectors = find_product_selectors(elements_results)
            print(f"Product Links LLM Response: {temp_product_selectors}")
            
            # Parse LLM response for product links
            product_link_selectors = json.loads(temp_product_selectors)
            
            file_path8 = "selectors/stage2_product_selectors.json"
            with open(file_path8, "w", encoding="utf-8") as f:
                json.dump(product_link_selectors, f, indent=4)
            
            # Step 12: Extract product links
            print("🔗 Extracting product links...")
            product_links = await extract_product_links(page, product_link_selectors, max_products=5)
            
            if product_links:
                # Step 13: Process products and extract reviews from dedicated review pages
                print("📝 Processing products and extracting reviews from review pages...")
                final_results = await process_products_and_reviews(page, product_links, max_products=1)
                
                # Add search query to results
                final_results['search_query'] = search_product
                
                # Save final results
                final_file_path = "extracted_date/final_result_llm_2.json"
                with open(final_file_path, "w", encoding="utf-8") as f:
                    json.dump(final_results, f, indent=4, ensure_ascii=False)
                
                print(f"🎉 All data extracted and saved to {final_file_path}")
                print(f"📊 Summary:")
                print(f"   - Search Query: {final_results['search_query']}")
                print(f"   - Products Found: {final_results['total_products_found']}")
                print(f"   - Products Processed: {final_results['products_processed']}")
                total_reviews = sum(p['reviews_found'] for p in final_results['products'])
                print(f"   - Total Reviews Extracted: {total_reviews}")
                
            else:
                print("❌ No product links found")
        
        else:
            print("❌ Product search failed")
        print("⏳ Waiting 10 seconds before closing...")
        await asyncio.sleep(10)
        await browser.close()
    print("✅ Pipeline completed")


if __name__ == "__main__":
    asyncio.run(run_pipeline())