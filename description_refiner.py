import os
import json
import re
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def refine_title_and_condition(title, description, original_condition):
    prompt = f"""
You are a product analysis assistant for eBay resale.

Given the original product title, description, and condition, your job is to:
1. Adjust the condition if the description reveals a major defect, serious malfunction, or anything that would require repair or make it unsuitable for resale as a working unit. This includes things like:
   - does not turn off
   - doesn't power on
   - stuck on one speed
   - error codes
   - damaged parts
   - broken screens
   - cannot charge or boot
If any of these or similar issues are present, change the condition to **"for parts"** even if the original condition says "used".

Be especially alert when the title includes phrases like "READ DESC" — this usually means there is an issue explained in the description.

Choose a condition from this exact list:
  - "new"
  - "open box"
  - "certified refurbished"
  - "seller refurbished"
  - "used"
  - "for parts"

2. Generate a resale-focused search query that keeps the useful structure of the original title but also adds important resale-impacting info from the description.
   - Do not make the title overly long or overly generic.
   - Only add critical flaws or missing parts.

3. Examples:
   - TITLE: "Kitchen Aid Stand Mixer Model #KSM90 With Bowl & Whisk Attachment READ DESC"
     DESCRIPTION: "does not turn off"
     → refined_query: "Kitchen Aid Stand Mixer KSM90 does not turn off"
     → adjusted_condition: "for parts"

   - TITLE: "KitchenAid KSM90 300W Ultra Power Stand Mixer White"
     DESCRIPTION: "missing bowl"
     → refined_query: "KitchenAid KSM90 Stand Mixer missing bowl"
     → adjusted_condition: "used"

   - TITLE: "Play Station 5 console only"
     DESCRIPTION: "no controller or cords"
     → refined_query: "Play Station 5 console only"
     → adjusted_condition: "used"

   - If it says "Only used a couple times" and the original condition was "new", downgrade to "used".
   - If the description is empty or provides no new information, simplify the original title slightly.

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
