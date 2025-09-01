from  selector_categorizer import SelectorCategorizer
import os
import json
import time
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
from groq import Groq
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

async def ask_ai_local_model(prompt: str, system_prompt: str,model_name:str) -> str:
        """
        Query local LM model using the same interface as test_lm_studio_model_conn.py
        
        Args:
            prompt: User prompt
            system_prompt: System prompt
            
        Returns:
            str: Model response content
        """
        async with httpx.AsyncClient(timeout=1200) as client:
            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 4000,
                "stream": False
            }
            resp = await client.post(f"http://localhost:1234/v1/chat/completions", json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        
def local_ai_selector_categorizer(selectors: list[dict], model_name: str) -> list[dict]:
    categorizer = SelectorCategorizer(provider="local")
    model = "qwen/qwen3-4b-2507"
    all_selectors = categorizer.prepare_all_selectors(selectors)
    total_selectors = len(all_selectors)
    if total_selectors == 0:
            print("⚠️ No selectors found to categorize")
            return categorizer.create_empty_categorization()
    
    final_result = []
    batch_size = 20 
    batches = [all_selectors[i:i + batch_size] for i in range(0, total_selectors, batch_size)]
    total_batches = len(batches)

    api_call_count = 0
    successful_batches = 0
    total_categorized_count = 0

    for batch_idx, batch in enumerate(batches, 1):
            print(f"\n🔄 Processing batch {batch_idx}/{total_batches} ({len(batch)} selectors)...")
            
            try:
                # Create the prompt for this batch
                system_role = categorizer.get_system_role()
                prompt = categorizer.create_categorization_prompt(batch)
                
                response_content = asyncio.run(ask_ai_local_model(prompt, system_role,model_name))

                api_call_count += 1
                
                # Clean up the response (remove any markdown formatting)
                if response_content.startswith("```json"):
                    response_content = response_content[7:]
                if response_content.endswith("```"):
                    response_content = response_content[:-3]
                
                batch_result = json.loads(response_content)
                
                # Process simple array format: [{"category": "...", "uuid": "...", "confidence": 0.85}]
                if isinstance(batch_result, list):
                    final_result.extend(batch_result)
                    total_categorized_count += len(batch_result)
                
                successful_batches += 1
                print(f"✅ Batch {batch_idx} processed successfully ({len(batch_result) if isinstance(batch_result, list) else 0} categorized)")
                time.sleep(3)
                
            except json.JSONDecodeError as e:
                print(f"❌ JSON parsing error in batch {batch_idx}: {e}")
                print(f"❌ Bad Prompt {prompt}")
                print(f"Raw response: {response_content[:200]}...")
                continue
                
            except Exception as e:
                print(f"❌ API error in batch {batch_idx}: {e}")
                continue
    
    print(f"\n🎉 Batch processing completed!")
    print(f"   Total batches: {total_batches}")
    print(f"   Successful batches: {successful_batches}")
    print(f"   Total selectors categorized: {total_categorized_count}")
    print(f"   API calls made: {api_call_count}")
    
    if successful_batches == 0:
        print("⚠️ No batches were successful, using fallback categorization")
        return categorizer.create_fallback_categorization(selectors)
    
    return final_result
    


    