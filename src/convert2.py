# convert2.py
from bs4 import BeautifulSoup
import json

def extract_elements(input_file: str, output_file: str):
    with open(input_file, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    elements = []

    for tag in soup.find_all(True):
        element_data = {
            "tag": tag.name,
            "id": tag.get("id"),
            "name": tag.get("name"),
            "type": tag.get("type"),
            "class": tag.get("class"),
            "text": tag.get_text(strip=True)[:50]
        }
        elements.append(element_data)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(elements, f, indent=2)

    print(f"✅ Extracted {len(elements)} elements → {output_file}")
    
if __name__ == "__main__":
    extract_elements("stage1_login.html", "stage1_elements.json")