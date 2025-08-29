import json
import sys

def extract_login_candidates(input_file, output_file="selectors/login_candidates.json"):
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    candidates = []

    # Keywords to catch login/signin buttons/links
    keywords = ["login", "log in", "sign in", "signin", "account"]

    # Collect buttons
    buttons = data.get("selectors_by_type", {}).get("buttons", {}).get("elements", [])
    for b in buttons:
        text = b.get("text", "").lower()
        attrs = " ".join(str(v).lower() for v in b.get("attrs", {}).values())

        if any(k in text for k in keywords) or any(k in attrs for k in keywords):
            b["source"] = "button"
            candidates.append(b)

    # Collect links
    links = data.get("selectors_by_type", {}).get("links", {}).get("elements", [])
    for l in links:
        text = l.get("text", "").lower()
        attrs = " ".join(str(v).lower() for v in l.get("attrs", {}).values())

        if any(k in text for k in keywords) or any(k in attrs for k in keywords):
            l["source"] = "link"
            candidates.append(l)

    # Write filtered results
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"login_candidates": candidates}, f, indent=2)

    return candidates

