import json

data = {}
file = "extracted_data/categorized_selectors/home_categorized.json"

try:
    with open(file, 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"Error: File '{file}' not found")
    exit()
except json.JSONDecodeError:
    print(f"Error: Invalid JSON in file '{file}'")
    exit()

target_uuid = "9cd43198-3e83-4bab-a083-cac64b23fcff"
found_class = None

# Check if data is a list (array) instead of a dictionary
if isinstance(data, list):
    print("Data is a list (array structure)")
    # Search through the list of items
    for item in data:
        if item.get("uuid") == target_uuid:
            # Check if the item has a class/category field
            if "class" in item:
                found_class = item["class"]
            elif "category" in item:
                found_class = item["category"]
            else:
                found_class = "Unknown class (no class/category field found)"
            break

elif isinstance(data, dict):
    print("Data is a dictionary (key-value structure)")
    # Original search logic for dictionary structure
    for key, values in data.items():
        for item in values:
            if item.get("uuid") == target_uuid:
                found_class = key
                break
        if found_class:
            break
else:
    print(f"Unexpected data type: {type(data)}")

if found_class:
    print(f"UUID {target_uuid} belongs to class: {found_class}")
else:
    print(f"UUID {target_uuid} not found")