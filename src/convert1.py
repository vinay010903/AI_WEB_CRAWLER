import json
import os
from playwright.sync_api import sync_playwright
from convert_base import extract_candidates, wait_for_page_stability


def extract_all_selectors(page, url, output_file="selectors/stage1_selectors.json", stage="initial"):
    """
    Navigates to a URL, extracts all interactive element selectors with context,
    and saves them to a JSON file.
    """
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        wait_for_page_stability(page)

        html_content = page.content()
        candidates = extract_candidates(html_content, base_url=url, stage=stage)

        selectors_data = {
            "url": url,
            "stage": stage,
            "total_candidates": len(candidates),
            "selectors_by_type": {
                "buttons": {
                    "selector": "button",
                    "count": len([c for c in candidates if c["tag"] == "button"]),
                    "elements": [c for c in candidates if c["tag"] == "button"]
                },
                "links": {
                    "selector": "a", 
                    "count": len([c for c in candidates if c["tag"] == "a"]),
                    "elements": [c for c in candidates if c["tag"] == "a"]
                },
                "inputs": {
                    "selector": "input",
                    "count": len([c for c in candidates if c["tag"] == "input"]),
                    "elements": [c for c in candidates if c["tag"] == "input"]
                },
                "spans": {
                    "selector": "span",
                    "count": len([c for c in candidates if c["tag"] == "span"]),
                    "elements": [c for c in candidates if c["tag"] == "span"]
                },
                "divs": {
                    "selector": "div",
                    "count": len([c for c in candidates if c["tag"] == "div"]),
                    "elements": [c for c in candidates if c["tag"] == "div"]
                }
            },
            "all_candidates": candidates
        }

        output_dir = os.path.dirname(output_file) if os.path.dirname(output_file) else "selectors"
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(selectors_data, f, indent=4, ensure_ascii=False)

        return output_file
    except Exception:
        return None