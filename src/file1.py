import json
import os

def extract_login_candidates():
    input_file = "selectors/test_selectors.json"
    output_file = "selectors/login_candidates.json"

    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    candidates = []
    keywords = ["login", "log in", "sign in", "signin", "account"]

    # Buttons
    buttons = data.get("selectors_by_type", {}).get("buttons", {}).get("elements", [])
    for b in buttons:
        text = b.get("text", "").lower()
        attrs = " ".join(str(v).lower() for v in b.get("attrs", {}).values())
        if any(k in text for k in keywords) or any(k in attrs for k in keywords):
            b["source"] = "button"
            candidates.append(b)

    # Links
    links = data.get("selectors_by_type", {}).get("links", {}).get("elements", [])
    for l in links:
        text = l.get("text", "").lower()
        attrs = " ".join(str(v).lower() for v in l.get("attrs", {}).values())
        if any(k in text for k in keywords) or any(k in attrs for k in keywords):
            l["source"] = "link"
            candidates.append(l)

    # Save
    os.makedirs("selectors", exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"login_candidates": candidates}, f, indent=2)

    print(f"✅ Found {len(candidates)} login candidates. Saved to {output_file}")


if __name__ == "__main__":
    extract_login_candidates()
