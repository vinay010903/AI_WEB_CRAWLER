import json
from pathlib import Path
from groq import Groq  
from dotenv import load_dotenv
import os
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) 

def call_llm(prompt: str) -> str:
    """Call LLM and return response text"""
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[
            {"role": "system", "content": "You are a strict JSON generator. Output ONLY valid JSON, nothing else."},
            {"role": "user", "content": prompt}
        ],
        temperature=0,
        max_tokens=512,
    )
    return response.choices[0].message.content.strip()

def safe_parse_json(text: str):
    """Try parsing JSON, otherwise extract JSON substring"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Attempt to extract JSON block if LLM added extra text
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
        # Or maybe it's a list
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except json.JSONDecodeError:
                pass
    return None

def select_top3(input_file, output_file):
    with open(input_file, "r") as f:
        data = json.load(f)

    prompt = f"""
You are given a JSON file with login_candidates. 
Pick the BEST hover_selector and login_selector pair. 
Return output strictly in JSON format like this:

[
  {{
    "hover_selector": "CSS_SELECTOR_STRING",
    "login_selector": "CSS_SELECTOR_STRING"
  }}
]
    
Input JSON:
{json.dumps(data, indent=2)}
"""

    result_text = call_llm(prompt)
    result = safe_parse_json(result_text)

    if result is None:
        raise ValueError(f"❌ LLM did not return valid JSON. Got:\n{result_text}")

    with open(output_file, "w") as f:
        json.dump(result, f, indent=4)

    print(f"✅ Selectors written to {output_file}")

if __name__ == "__main__":
    input_file = "selectors/login_candidates.json"
    output_file = "selectors/final2.json"
    select_top3(input_file, output_file)