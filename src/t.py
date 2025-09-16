import json
main_grouped_file = "extracted_data/grouped_selectors/main_grouped.json"
res={}
with open(main_grouped_file, "r") as f:
    res = json.load(f)

for key,value in res.items():
    print(key)