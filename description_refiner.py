import os
import json
import re
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def refine_title_and_condition(title, description, original_condition):
    prompt = f"""
You are a product analysis assistant for eBay resale.

Given the original product title, description, and condition, your job is to:
1. Adjust the condition ONLY if the description clearly contradicts the original. Be especially aware of items which say "Read Description" in the title as they usually have a defect and are not working. Choose a condition from this exact list:
   - "new"
   - "open box"
   - "certified refurbished"
   - "seller refurbished"
   - "used"
   - "for parts/not working"
2. Generate a resale-focused search query that copies the original title but also accurately adds information from the description
3. In addition to the information provided from the title, include information from the description which might have an impact on resale price. Pay special attention to titles which say something like "read description" as they typically explain what is wrong with an item. Make sure that information in the description which is relevant (ex. missing bowl, console only, or otherwise) is included in the new search query. If there is no relevant information in the description or it is empty, do not alter the new search query. If there is information in the description that is already represented in the new search query you may ignore it.

Here are some example situations:
   - If the title says "Kitchen Aid Stand Mixer Model #KSM90 With Bowl & Whisk Attachment READ DESC" make sure to **read the description**, if the description says "Tested & working but does not turn off" the new search should be "Kitchen Aid Stand Mixer Model #KSM90 With Bowl & Whisk Attachment does not turn off" and the condition should be "for parts"
   - If the description for "KitchenAid KSM90 300W Ultra Power Stand Mixer White" says it is is missing the bowl, say: "KitchenAid KSM90 300W Ultra Power Stand Mixer White missing bowl"
   - If a title says "Play Station 5 console only", and the description says "no controller or cords" the new query can just be "Playstation 5 console only"
   - If it says "brand new", and the condition is already "new", you can ignore that.
   - If it says "Only used a couple times" and the condition said "new" change it to "used".
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
