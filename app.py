# --- app.py ---
from fastapi import FastAPI, HTTPException, Body,  Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional
import requests
import json
from openai import OpenAI
import time
import base64
import os
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

ROI_THRESHOLD = 0.1  # Minimum ROI (30%) required for all 5 items
import traceback
import re
load_dotenv()
print("🔑 OpenAI API Key:", os.getenv("OPENAI_API_KEY"))

from models import Base, User, SavedItem, SessionLocal, engine
from sqlalchemy.orm import Session

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://flipfinderwebsite.onrender.com"],  # Your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID", "your-ebay-client-id")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET", "your-ebay-client-secret")
EBAY_OAUTH_TOKEN = None
EBAY_TOKEN_EXPIRY = 0

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
client = OpenAI(api_key=OPENAI_API_KEY)

# Dependency for DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Signup model
class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

@app.post("/signup")
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter((User.username == data.username) | (User.email == data.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already exists")

    new_user = User(username=data.username, email=data.email)
    new_user.set_password(data.password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "user_id": new_user.id}

@app.post("/login")
def login(data: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data["email"]).first()
    if not user or not user.verify_password(data["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"message": "Login successful", "username": user.username}

@app.post("/save_item")
def save_item(data: dict = Body(...), db: Session = Depends(get_db)):
    username = data.get("username")
    item = data.get("item")

    if not username or not item:
        raise HTTPException(status_code=400, detail="Missing username or item")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check for duplicate
    existing = db.query(SavedItem).filter(SavedItem.user_id == user.id, SavedItem.url == item["url"]).first()
    if existing:
        return {"message": "Already saved"}

    new_item = SavedItem(
        user_id=user.id,
        title=item["title"],
        price=item["price"],
        profit=item["profit"],
        thumbnail=item["thumbnail"],
        url=item["url"]
    )
    db.add(new_item)
    db.commit()
    return {"message": "Item saved successfully"}

@app.get("/saved_items/{username}")
def get_saved_items(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    items = db.query(SavedItem).filter(SavedItem.user_id == user.id).all()

    return [
        {
            "title": item.title,
            "price": item.price,
            "profit": item.profit,
            "thumbnail": item.thumbnail,
            "url": item.url
        } for item in items
    ]


# --- AI/Ebay Search Logic Below ---

def get_ebay_token():
    global EBAY_OAUTH_TOKEN, EBAY_TOKEN_EXPIRY
    if EBAY_OAUTH_TOKEN and time.time() < EBAY_TOKEN_EXPIRY - 60:
        return EBAY_OAUTH_TOKEN

    url = "https://api.ebay.com/identity/v1/oauth2/token"
    credentials = f"{EBAY_CLIENT_ID}:{EBAY_CLIENT_SECRET}"
    headers = {
        "Authorization": f"Basic {base64.b64encode(credentials.encode()).decode()}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }
    response = requests.post(url, headers=headers, data=data)
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Failed to refresh eBay token")

    token_data = response.json()
    EBAY_OAUTH_TOKEN = token_data["access_token"]
    EBAY_TOKEN_EXPIRY = time.time() + int(token_data["expires_in"])
    return EBAY_OAUTH_TOKEN

class NaturalQuery(BaseModel):
    search: str

def parse_search_criteria(natural_input):
    prompt = f"""
You are a smart resale assistant.

Extract a clean, structured search intent from the user's input below.

Make sure:
- 'query' only includes the product name (no extra words or qualifiers) and should only be a few words long (2-3) (with an emphasis on brand names)
- 'condition' reflects the user's tolerance for damage (e.g., 'used' if they accept problems)
- 'include_terms' should highlight key features or models
- 'exclude_terms' should reflect things the user wants to avoid
- do not however, add included/excluded terms unledd the search input specifies qualities which the individual is looking for and thus would be relevant to filter 

User input:
\"{natural_input}\"

Return JSON with:
- query: string (main product)
- condition: "used", "new", or "any"
- include_terms: list of keywords to match in title
- exclude_terms: list of keywords to avoid

Example format:
{{
  "query": "AirPods Pro Max",
  "condition": "used",
  "include_terms": ["scratches"],
  "exclude_terms": []
}}
"""
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ]
    )

    try:
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```json"):
            raw = raw.removeprefix("```json").strip()
        if raw.endswith("```"):
            raw = raw.removesuffix("```").strip()
        raw = re.sub(r",(\s*[}\]])", r"\\1", raw)  # remove trailing commas
        return json.loads(raw)
    except Exception as e:
        print("Failed to parse OpenAI response:", response.choices[0].message.content)
        raise HTTPException(status_code=500, detail="Failed to parse OpenAI response")


def refined_avg_price(title):
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    headers = {
        "Authorization": f"Bearer {get_ebay_token()}",
        "Content-Type": "application/json",
    }
    params = {
        "q": title,
        "limit": "10"
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        return 0
    data = response.json()
    items = data.get("itemSummaries", [])
    prices = [float(item["price"]["value"]) for item in items if "price" in item]
    return sum(prices) / len(prices) if prices else 0

import asyncio

def search_ebay(parsed, original_input):
    def run_ebay_search(query, condition, include_terms, exclude_terms):
        url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
        headers = {
            "Authorization": f"Bearer {get_ebay_token()}",
            "Content-Type": "application/json",
        }
        filters = []
        if condition == "used":
            filters.append("conditionIds:{3000}")
        elif condition == "new":
            filters.append("conditionIds:{1000}")
        filter_str = ",".join(filters) if filters else None

        params = {
            "q": query,
            "limit": "80",
        }
        print("📦 Sending eBay query:", query)
        if filter_str:
            params["filter"] = filter_str

        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            print("eBay API error:", response.text)
            return []

        data = response.json()
        return data.get("itemSummaries", [])

    def extract_shipping_cost(item):
        try:
            options = item.get("shippingOptions", [])
            if not options:
                return 0.0

            cost_data = options[0].get("shippingCost", {})
            if "value" in cost_data:
                return float(cost_data["value"])
            
            # Catch "CALCULATED" or "NOT_SPECIFIED" types that aren't numeric
            if cost_data.get("type") in ["CALCULATED", "NOT_SPECIFIED"]:
                print(f"⚠️ Shipping cost type is {cost_data.get('type')} — skipping item: {item.get('title')}")
                return 0.0

            return 0.0
        except Exception as e:
            print(f"⚠️ Error extracting shipping from item: {item.get('title')}")
            print(e)
            return 0.0


    def calculate_profit(item):
        price = float(item.get("price", {}).get("value", 0))
        shipping = extract_shipping_cost(item)
        total_price = price + shipping
        refined_resale = refined_avg_price(item.get("title", ""))
        profit = (refined_resale * 0.85) - total_price
        roi = round(profit / total_price, 2) if total_price > 0 else 0
        return total_price, profit, roi, price, shipping

    def filter_and_score(items, include_terms, exclude_terms):
        filtered = []
        for item in items:
            title = item.get("title", "").lower()

            if any(term.lower() in title for term in exclude_terms):
                continue
            if not all(term.lower() in title for term in include_terms):
                continue

            total_price, profit_value, roi, item_price, shipping = calculate_profit(item)

            if profit_value <= 0:
                continue

            filtered.append({
                "title": item.get("title"),
                "price": total_price,
                "item_price": item_price,
                "shipping": shipping,
                "profit": profit_value,
                "roi": roi,
                "profit_color": "green",
                "thumbnail": item.get("image", {}).get("imageUrl"),
                "url": item.get("itemWebUrl")
            })
            print("🧾 Final listing selected:")
            print(json.dumps({
                "title": item.get("title"),
                "price": item.get("price", {}).get("value"),
                "shippingOptions": item.get("shippingOptions"),
                "url": item.get("itemWebUrl")
            }, indent=2))


        return filtered

    query = parsed["query"]
    condition = parsed.get("condition", "any")
    include_terms = parsed.get("include_terms", [])
    exclude_terms = parsed.get("exclude_terms", [])

    all_results = []
    seen_titles = set()
    iteration = 0
    max_iterations = 10

    def try_query(q, cond, includes, excludes):
        raw_items = run_ebay_search(q, cond, includes, excludes)
        results = filter_and_score(raw_items, includes, excludes)
        for r in results:
            if r["title"] not in seen_titles:
                all_results.append(r)
                seen_titles.add(r["title"])
            if len(all_results) >= 5 and all(item["roi"] >= ROI_THRESHOLD for item in sorted(all_results, key=lambda x: x["profit"], reverse=True)[:5]):
                break

    try_query(query, condition, include_terms, exclude_terms)
    if len(all_results) >= 5 and all(item["roi"] >= ROI_THRESHOLD for item in sorted(all_results, key=lambda x: x["profit"], reverse=True)[:5]):
        return sorted(all_results, key=lambda x: x["profit"], reverse=True)[:5]

    print("⏳ Waiting for initial eBay results...")
    time.sleep(3)
    if len(all_results) >= 5 and all(item["roi"] >= ROI_THRESHOLD for item in sorted(all_results, key=lambda x: x["profit"], reverse=True)[:5]):
        return sorted(all_results, key=lambda x: x["profit"], reverse=True)[:5]

    original_query = query
    original_include_terms = include_terms[:]
    original_exclude_terms = exclude_terms[:]

    while (len(all_results) < 5 or not all(item["roi"] >= ROI_THRESHOLD for item in sorted(all_results, key=lambda x: x["profit"], reverse=True)[:5])) and iteration < max_iterations:
        if len(all_results) >= 5 and all(item["roi"] >= ROI_THRESHOLD for item in sorted(all_results, key=lambda x: x["profit"], reverse=True)[:5]):
            break
        prompt = f"""
You're helping refine a resale-related eBay search based on a user's original message.

User's full original search message:
\"{original_input}\"

Original parsed intent:
- Query: \"{original_query}\"
- Condition: {condition}
- Include terms: {original_include_terms}
- Exclude terms: {original_exclude_terms}

Previous fallback search attempt:
- Query: \"{query}\"
- Include terms: {include_terms}
- Exclude terms: {exclude_terms}
- Only {len(all_results)} results found.

Please try a **new, independent** eBay-style search query:
- Do not copy the previous fallback search query, instead search something that is different yet fundamentally related to the original seearch query
- Additionally, do not make adjustments to included and excluded terms by removing, changing, or finding synonms for them
- Reword the `query` to be simpler or more natural for eBay titles. The query must be only a few words long (2-3) (with an emphasis on brand names)
- You may simplify or remove unnecessary words from the query and move them to include_terms.
- Do NOT ignore the user's intent — especially things like condition or tolerance for scratches, damage, etc.
- Please feel free to change any included and excluded terms, but make sure they are still connected to or relevant to the original search query
- Do NOT add unrelated words like "flipping", "resale", or adjectives like "mint", unless the user originally said so.

Return ONLY valid JSON:
{{
  "query": "short new search string",
  "condition": "{condition}",
  "include_terms": {json.dumps(include_terms)},
  "exclude_terms": {json.dumps(exclude_terms)}
}}
"""



        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You help refine search criteria for resale flipping."},
                {"role": "user", "content": prompt}
            ]
        )

        try:
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```json"):
                raw = raw.removeprefix("```json").strip()
            if raw.endswith("```"):
                raw = raw.removesuffix("```").strip()
            raw = re.sub(r",(\s*[}\]])", r"\\1", raw)
            parsed_fallback = json.loads(raw)

            query = parsed_fallback.get("query", query)
            condition = parsed_fallback.get("condition", condition)
            include_terms = parsed_fallback.get("include_terms", include_terms)
            exclude_terms = parsed_fallback.get("exclude_terms", exclude_terms)

            print("🔄 Iteration", iteration + 1, "- GPT query:", json.dumps(query), json.dumps(include_terms))
            try_query(query, condition, include_terms, exclude_terms)
            if len(all_results) >= 5 and all(item["roi"] >= ROI_THRESHOLD for item in sorted(all_results, key=lambda x: x["profit"], reverse=True)[:5]):
                break
        except Exception as e:
            print("⚠️ Failed to parse GPT fallback response:", e)
            break

        iteration += 1

    return sorted(all_results, key=lambda x: x["profit"], reverse=True)[:5]

@app.post("/ai_search")
def ai_search(nq: NaturalQuery):
    try:
        parsed = parse_search_criteria(nq.search)
        print("🔍 AI INTERPRETATION:")
        print(json.dumps(parsed, indent=2))
        results = search_ebay(parsed, nq.search)

        # ✅ Count ROI-qualified items (ROI >= 0.5)
        qualified_count = sum(1 for item in results if item.get("roi", 0) >= 0.5)

        return {
            "parsed": parsed,
            "results": results,
            "qualified_count": qualified_count  # ✅ add to response
        }

    except Exception as e:
        print("X full error traceback:")
        traceback.print_exc()
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Something went wrong.")

try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    import traceback
    print("❌ Error running Base.metadata.create_all")
    traceback.print_exc()
