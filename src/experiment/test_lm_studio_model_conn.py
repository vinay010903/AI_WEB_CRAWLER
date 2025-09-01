import httpx, asyncio

async def ask(prompt: str, system_prompt: str = "You are a helpful assistant.", model="openai/gpt-oss-20b"):
    async with httpx.AsyncClient(timeout=1200.0) as client:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": prompt}
            ],
            "max_tokens": 4000,
        }
        resp = await client.post("http://localhost:1234/v1/chat/completions", json=payload)
        return resp.json()["choices"][0]["message"]["content"]

async def main():
    system = """
        CATEGORIES (use these exact keys in your response):
        1. "navigation_layout" - Headers, footers, menus, breadcrumbs, structural layout components
        2. "authentication_account" - Login, registration, user profile, account settings, authentication elements
        3. "search_filters" - Search bars, filters, sorting controls, query inputs
        4. "category_listing" - Category pages, product grids, product cards, listing containers, pagination
        5. "product_details" - Product page elements: specifications, reviews, ratings, add to cart, buy now, product images
        6. "support_misc" - Help, contact, customer service, notifications, alerts, miscellaneous site elements
        7. "uncategorized_selector" - Ambiguous or selectors that don’t clearly fit into any above category

        INSTRUCTIONS:
        1. Use selector name, HTML tag, attributes, and text content for classification.
        2. Apply common web conventions to infer intent (e.g., `#search-bar`, `.login-form`, `#product-grid`).
        3. Choose the PRIMARY function of the element; if unclear, use "uncategorized_selector".
        4. Assign a confidence score between 0 and 1 (two decimal places).
        5. Provide ONLY the required JSON format.

        OUTPUT FORMAT (strict JSON only, no extra text):
        [
            { "category": "<category>", "uuid": "selector_uuid", "confidence": 0.85 }
        ]
        """
    prompt = """
        SELECTORS TO CATEGORIZE:
        [{
            "uuid": "4d4634de-92e1-4bf4-ab37-f03448648a8d",
            "selector": "#nav-tools",
            "tag": "div",
            "text_content": "ENHello, sign inAccount & ListsReturns& Orders0Cart"
        },
        {
            "uuid": "ccb1e695-0de9-42e5-9bc6-b51a1761661d",
            "selector": "#icp-nav-flyout",
            "tag": "div",
            "text_content": "EN"
        },
        {
            "uuid": "77d5eca2-01e9-4187-9de7-2a95eeb8588c",
            "selector": "#nav-link-accountList",
            "tag": "div",
            "text_content": "Hello, sign inAccount & Lists"
        },
        {
            "uuid": "f94e53b7-df3a-44a1-831e-e91f203c1b1c",
            "selector": "#nav-link-accountList-nav-line-1",
            "tag": "span",
            "text_content": "Hello, sign in"
        },
        {
            "uuid": "fdef0d0c-d3c9-49f6-b1ec-b6104d27ff09",
            "selector": "#nav-orders",
            "tag": "a",
            "text_content": "Returns& Orders"
        }]
    """
    answer = await ask(system_prompt=system,prompt=prompt)
    print(answer)

asyncio.run(main())
