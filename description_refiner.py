import os
import json
import re
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def refine_title_and_condition(title, description, original_condition):
    prompt = f"""
You are a product analysis assistant for eBay resale.

Given the original product title, description, and condition, your job is to:
1. Adjust the condition ONLY if the description clearly contradicts the original. Choose from this exact list:
   - "new"
   - "open box"
   - "certified refurbished"
   - "seller refurbished"
   - "used"
   - "for parts/not working"
2. Generate a short resale-focused search query (2-6 words) that accurately reflects the condition and any significant issue (e.g., missing parts, not working).
3. Do NOT overfit the query. Keep it simple, and if you are unsure, coose to make the search more broad. If there is no relevant information in the query or it is empty, do not alter the search query. For example:
   - If a "KitchenAid Mixer" is missing the bowl, say: "KitchenAid mixer missing bowl"
   - If it says "works great", and the condition is already "new", you can ignore that.
   - If no major issue is found, simplify the original title for a clean search query.
   - Description empty, simplify the original title for a clean search query.

Inputs:
- TITLE: {title}
- DESCRIPTION: {description}
- ORIGINAL CONDITION: {original_condition}

Respond ONLY in this format:
{{
  "refined_query": "...",
  "adjusted_condition": "new" | "open box" | "certified refurbished" | "seller refurbished" | "used" | "for parts"
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You refine eBay product listings for resale search accuracy."},
                {"role": "user", "content": prompt}
            ]
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```json"):
            raw = raw.removeprefix("```json").strip()
        if raw.endswith("```"):
            raw = raw.removesuffix("```").strip()
        raw = re.sub(r",(\s*[}\]])", r"\1", raw)
        return json.loads(raw)
    except Exception as e:
        print("❌ GPT refinement failed:", e)
        return {
            "refined_query": title,
            "adjusted_condition": original_condition
        }
