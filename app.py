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
import asyncio
message_queue = asyncio.Queue()
import datetime
from auto_search import auto_search_bp
from description_refiner import refine_title_and_condition
from password_reset import router as reset_router
from pydantic import BaseModel
from db import get_db
import statistics
from price_estimator import refined_avg_price
from fastapi import Request
import httpx
from urllib.parse import quote






def log_event(event_type: str, details: str):
    timestamp = datetime.datetime.now().isoformat()
    with open("analytics.log", "a") as log_file:
        log_file.write(f"[{timestamp}] {event_type}: {details}\n")


ROI_THRESHOLD = 0.1  # Minimum ROI (30%) required for all 5 items
import traceback
import re
load_dotenv()
#print("🔑 OpenAI API Key:", os.getenv("OPENAI_API_KEY"))

from models import Base, User, SavedItem, SavedSearch, SessionLocal, engine
from models import User, SavedSearch, SavedItem, SearchResultSnapshot, EmailedListing

from sqlalchemy.orm import Session

app = FastAPI()

refined_cache = {}


app.include_router(reset_router)
app.include_router(auto_search_bp)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://flipfinderwebsite.onrender.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://resale-radar.com",
        "https://www.resale-radar.com",
        "null"
    ],
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

class ChangeEmailRequest(BaseModel):
    old_email: str
    new_email: str

class NaturalQuery(BaseModel):
    search: str
    postalCode: str | None = None
    city: str | None = None
    state: str | None = None

from urllib.parse import quote
import json
import traceback
import time


@app.post("/ksl_deals")
async def ksl_deals(nq: NaturalQuery):
    start_time = time.time()
    try:
        query = nq.search or ""
        state = nq.state or ""
        print(f"\n🟢 /ksl_deals started for: {query} [{state}]")

        safe_query = quote(query)
        safe_state = quote(state)

        async def fetch_and_process(scrape_query, label="main"):
            try:
                encoded = quote(scrape_query)
                url = f"https://ksl-scraper.onrender.com/ksl?query={encoded}&state={safe_state}"
                print(f"🌐 [{label}] URL:", url)

                async with httpx.AsyncClient(timeout=120) as client:
                    res = await client.get(url)
                    if res.status_code != 200:
                        print(f"❌ [{label}] Request failed")
                        return []

                    raw_text = res.text
                    raw_json = json.loads(raw_text)
                    print(f"📦 [{label}] Listings returned:", len(raw_json))

                    results = await asyncio.gather(*[
                        process_listing(l, i) for i, l in enumerate(raw_json[:30])
                    ])
                    return [r for r in results if r]
            except Exception:
                print(f"❌ Exception in [{label}] processing:")
                traceback.print_exc()
                return []

        async def gpt_ksl_fallback_query(original_input: str, iteration: int):
            prompt = f"""
You're helping with a local classified search (KSL). Your goal is to simplify the user's original query into short, high-quality search terms that match titles on a local resale website.

Guidelines:
- The returned query must be **2–3 keywords only**
- Avoid unnecessary descriptors like "good condition", "missing parts", etc.
- Avoid filler like "used", "buy", or "cheap"
- NEVER repeat the original query exactly
- Emphasize brand and product type (e.g., "kitchenaid mixer", "nintendo switch lite")

Original user search:
"{original_input}"

Return ONLY valid JSON:
{{ "query": "simple product keywords" }}
"""
            print(f"⚙️ Running GPT fallback KSL query: iteration={iteration}")
            print(f"📩 Prompt sent to GPT:\n{prompt}")

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You simplify product search queries for local listings."},
                    {"role": "user", "content": prompt}
                ]
            )
            raw = response.choices[0].message.content.strip()
            if raw.startswith("```json"):
                raw = raw.removeprefix("```json").strip()
            if raw.endswith("```"):
                raw = raw.removesuffix("```").strip()
            raw = re.sub(r",(\s*[}\]])", r"\1", raw)
            print(f"📤 GPT raw response:\n{raw}")
            try:
                return json.loads(raw)["query"]
            except Exception:
                print(f"❌ Failed to parse fallback KSL query for iteration {iteration}:")
                traceback.print_exc()
                return None

        async def process_listing(listing, i):
            try:
                title = listing.get("title", "")
                if not title or not listing.get("price"):
                    return None

                

                # 💡 Process profit
                refinement = refine_title_and_condition(title, "", "used")
                resale = refined_avg_price(refinement["refined_query"], refinement["adjusted_condition"])
                price = float(listing["price"])
                profit = (resale * 0.85) - price
                roi = round(profit / price, 2)

                if roi < ROI_THRESHOLD:
                    return None
                # 🔄 Increment counter for live tracking
                await message_queue.put("increment")

                result = {
                    "title": title,
                    "price": price,
                    "profit": profit,
                    "roi": roi,
                    "location": listing.get("location"),
                    "datePosted": listing.get("datePosted"),
                    "url": listing.get("listingUrl"),
                    "thumbnail": listing.get("imageUrl"),
                    "refined_query": refinement["refined_query"],
                    "adjusted_condition": refinement["adjusted_condition"],
                    "_source": "ksl"
                }

                # ✅ Send to frontend immediately
                await message_queue.put(json.dumps({"type": "new_result", "data": result}))
                return result

            except Exception:
                print(f"❌ Error processing listing #{i}:")
                traceback.print_exc()
                return None


        # --- Main query first ---
        cleaned = await fetch_and_process(query, label="main")
        print(f"✅ Qualified listings after main: {len(cleaned)}")


        alt1 = None
        alt2 = None

        qualified_count = len([r for r in cleaned if r])
        if qualified_count < 5:
            print("🔁 Not enough KSL results — trying alt1")
            alt1 = await gpt_ksl_fallback_query(query, 1)
            if alt1:
                alt1_results = await fetch_and_process(alt1, label="alt1")
                cleaned += alt1_results

        print(f"✅ After alt1: {len(cleaned)}")


        qualified_count = len([r for r in cleaned if r])
        if qualified_count < 5:
            print("🔁 Still under 5 — trying alt2")
            alt2 = await gpt_ksl_fallback_query(query, 2)
            if alt2:
                alt2_results = await fetch_and_process(alt2, label="alt2")
                cleaned += alt2_results


        cleaned.sort(key=lambda x: x["profit"], reverse=True)
        total_time = round(time.time() - start_time, 2)
        print(f"✅ Finished /ksl_deals for: {query} | Returned: {len(cleaned)} | Time: {total_time}s")

        return {
            "results": cleaned[:5],
            "alt1": alt1,
            "alt2": alt2
        }

    except Exception as e:
        print("❌ General error in /ksl_deals:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="KSL processing failed")


@app.post("/request_password_reset")
def request_password_reset(email: str = Body(...), db: Session = Depends(get_db)):
    print("📨 Reset requested for:", email)
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found 1")

    # Continue with reset logic...
    return {"message": "Reset email sent"}


@app.post("/set_email_days")
def set_email_days(data: dict = Body(...), db: Session = Depends(get_db)):
    username = data.get("username")
    days = data.get("days", [])

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found 2")

    user.email_days = ",".join(str(day) for day in days)
    db.commit()
    return {"message": "Email days updated successfully"}



@app.post("/change_email")
def change_email(data: ChangeEmailRequest, db: Session = Depends(get_db)):
    # Check if new email is already in use
    if db.query(User).filter(User.email == data.new_email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    # Find current user by old email
    user = db.query(User).filter(User.email == data.old_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found 3")

    # Update the email
    user.email = data.new_email
    db.commit()
    return {"message": "Email updated successfully"}



# Signup model
class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str

@app.post("/delete_account")
def delete_account(data: dict = Body(...), db: Session = Depends(get_db)):
    user_email = data.get("userEmail").strip().lower()  # Normalize the email (trim and lowercase)
    print(user_email, "here is the email after")
    
    
    # Use a case-insensitive query and make sure to remove any extra whitespace
    user = db.query(User).filter(User.email == user_email).first()
    print(user.email, "user.email")

    if not user:
        raise HTTPException(status_code=404, detail=user_email)
    
    # Proceed with deletion if user is found
    db.query(SavedSearch).filter(SavedSearch.user_id == user.id).delete()
    db.query(SavedItem).filter(SavedItem.user_id == user.id).delete()
    db.query(SearchResultSnapshot).filter(SearchResultSnapshot.user_id == user.id).delete()
    db.query(EmailedListing).filter(EmailedListing.user_id == user.id).delete()
    
    db.delete(user)
    db.commit()

    #return {"message": "Account deleted"}



@app.get("/get_email/{username}")
def get_email(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found 4")
    return {"email": user.email}


@app.get("/get_email_days/{username}")
def get_email_days(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found 5")

    if user.email_days:
        try:
            return {"days": [int(d) for d in user.email_days.split(",") if d != ""]}
        except Exception:
            return {"days": []}
    return {"days": []}

@auto_search_bp.post("/disable_auto_search")
def disable_auto_search(data: dict = Body(...), db: Session = Depends(get_db)):
    username = data.get("username")
    query_text = data.get("query_text")

    if not username or not query_text:
        raise HTTPException(status_code=400, detail="Missing username or query_text")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found 6")

    existing = db.query(SavedSearch).filter_by(user_id=user.id, query_text=query_text).first()
    if not existing:
        raise HTTPException(status_code=404, detail="Search not found")

    existing.auto_search_enabled = False
    db.commit()
    return {"message": "Auto-search disabled"}

@app.post("/change_username")
def change_username(data: dict = Body(...), db: Session = Depends(get_db)):
    old = data.get("old_username")
    new = data.get("new_username")

    if not old or not new:
        raise HTTPException(status_code=400, detail="Missing usernames")

    if db.query(User).filter(User.username == new).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = db.query(User).filter(User.username == old).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found 7")

    user.username = new
    db.commit()

    return {"message": "Username updated"}

@app.post("/signup")
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    if db.query(User).filter((User.username == data.username) | (User.email == data.email)).first():
        raise HTTPException(status_code=400, detail="Username or email already exists")

    new_user = User(
        username=data.username,
        email=data.email,
        email_days="0,1,2,3,4,5,6"  # ✅ default to all days selected
    )
    new_user.set_password(data.password)

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # ✅ Log the signup
    log_event("User Signup", f"username={new_user.username}, email={new_user.email}")

    return {"message": "User created successfully", "user_id": new_user.id}

@app.post("/login")
def login(data: dict, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data["email"]).first()
    if not user or not user.verify_password(data["password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    log_event("User Login", f"username={user.username}, email={user.email}")
    return {"message": "Login successful", "username": user.username}

@app.post("/save_item")
def save_item(data: dict = Body(...), db: Session = Depends(get_db)):
    username = data.get("username")
    item = data.get("item")

    if not username or not item:
        raise HTTPException(status_code=400, detail="Missing username or item")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found 8")

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

@app.post("/unsave_item")
def unsave_item(data: dict = Body(...), db: Session = Depends(get_db)):
    username = data.get("username")
    item = data.get("item")

    if not username or not item:
        raise HTTPException(status_code=400, detail="Missing username or item")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found 9")

    # Delete saved item by URL
    deleted = db.query(SavedItem).filter_by(user_id=user.id, url=item["url"]).delete()
    db.commit()

    return {"message": "Item unsaved", "deleted_count": deleted}


@app.get("/saved_items/{username}")
def get_saved_items(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found 10")

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
@app.get("/saved_searches/{username}")
def get_saved_searches(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found 11")

    searches = db.query(SavedSearch).filter(SavedSearch.user_id == user.id).all()

    return [
        {
            "query_text": s.query_text,
            "auto_search_enabled": s.auto_search_enabled,
            "created_at": s.created_at.isoformat()
        } for s in searches
    ]

@app.post("/log_click")
def log_click(data: dict):
    url = data.get("url", "UNKNOWN")
    title = data.get("title", "No Title")
    user = data.get("username", "Anonymous")
    log_event("Item Click", f"user={user}, title={title}, url={url}")
    return {"message": "Click logged"}


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


def refined_avg_price(query, condition=None):
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    headers = {
        "Authorization": f"Bearer {get_ebay_token()}",
        "Content-Type": "application/json",
    }

    # eBay condition ID mapping
    condition_map = {
        "new": "1000",
        "open box": "1500",
        "certified refurbished": "2000",
        "seller refurbished": "2500",
        "used": "3000",
        "for parts": "7000",
        "not working": "7000",
        "any": None,
        "not specified": None
    }

    filters = []
    condition_key = condition.lower() if condition else None
    condition_id = condition_map.get(condition_key)
    if condition_id:
        filters.append(f"conditionIds:{{{condition_id}}}")
    filter_str = ",".join(filters) if filters else None

    params = {
        "q": query,
        "limit": "10"
    }
    if filter_str:
        params["filter"] = filter_str

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        return 0

    data = response.json()
    items = data.get("itemSummaries", [])
    prices = [float(item["price"]["value"]) for item in items if "price" in item]
    return statistics.median(prices) if prices else -999


import asyncio

def fetch_item_details(item_id):
    url = f"https://api.ebay.com/buy/browse/v1/item/{item_id}"
    headers = {
        "Authorization": f"Bearer {get_ebay_token()}",
        "Content-Type": "application/json",
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"⚠️ Failed to fetch item details for {item_id}: {response.status_code}")
        return {}


def search_ebay(parsed, original_input, postal_code=None):
    import asyncio
    import json
    import re

    def run_ebay_search(query, condition, include_terms, exclude_terms, postal_code=None):
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
            "limit": "30",
        }
        if postal_code and re.match(r"^\d{5}$", postal_code):
            params["buyerPostalCode"] = postal_code

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
        shipping_options = item.get("shippingOptions", [])
        if not shipping_options:
            print(f"⚠️ No shippingOptions found for item: {item.get('title')}")
            return None

        for option in shipping_options:
            shipping_type = option.get("shippingType", "").lower()
            if "pickup" in shipping_type:
                continue

            cost_data = option.get("shippingCost", {})
            if cost_data is not None and "value" in cost_data:
                cost = float(cost_data["value"])
                print(f"✅ Found shipping: ${cost:.2f} for {item.get('title')}")
                return cost

        print(f"❌ Only pickup found — skipping: {item.get('title')}")
        return None

    def calculate_profit(item, parsed_condition):
        def safe_enqueue_increment():
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(message_queue.put(json.dumps({"type": "increment"})))
            except RuntimeError:
                asyncio.run(message_queue.put(json.dumps({"type": "increment"})))

        for _ in range(26):
            safe_enqueue_increment()

        price = item["price"] if isinstance(item["price"], float) else float(item.get("price", {}).get("value", 0))

        if price <= 40:
            return None

        shipping = extract_shipping_cost(item)
        if shipping is None:
            return None

        total_price = price + shipping
        title = item.get("title", "").lower()
        description = ""

        suspicious_terms = ["read", "see desc", "as is", "untested", "issue"]
        if price > 100 and any(term in title for term in suspicious_terms):
            item_id = item.get("itemId", "")
            full_item = fetch_item_details(item_id)
            description = full_item.get("description", "")

        refinement = refine_title_and_condition(title, description, parsed_condition)
        refined_query = refinement["refined_query"]
        adjusted_condition = refinement["adjusted_condition"]

        cache_key = (refined_query, adjusted_condition)
        if cache_key in refined_cache:
            refined_resale = refined_cache[cache_key]
        else:
            refined_resale = refined_avg_price(refined_query, adjusted_condition)
            refined_cache[cache_key] = refined_resale

        profit = (refined_resale * 0.85) - total_price
        roi = round(profit / total_price, 2) if total_price > 0 else 0

        return total_price, profit, roi, price, shipping, refined_query, adjusted_condition, description

    def filter_and_score(items, include_terms, exclude_terms):
        for item in items:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(message_queue.put(json.dumps({"type": "increment"})))
            except RuntimeError:
                asyncio.run(message_queue.put(json.dumps({"type": "increment"})))

            title = item.get("title", "").lower()

            if any(term.lower() in title for term in exclude_terms):
                continue
            if not all(term.lower() in title for term in include_terms):
                continue

            result = calculate_profit(item, condition)
            if result is None:
                continue

            total_price, profit_value, roi, item_price, shipping, refined_query, adjusted_condition, description = result
            if shipping is None or profit_value <= 0:
                continue

            result_obj = {
                "title": item.get("title"),
                "price": total_price,
                "item_price": item_price,
                "description": description,
                "shipping": shipping,
                "profit": profit_value,
                "roi": roi,
                "profit_color": "green",
                "thumbnail": item.get("image", {}).get("imageUrl"),
                "url": item.get("itemWebUrl"),
                "refined_query": refined_query,
                "adjusted_condition": adjusted_condition
            }
            all_results.append(result_obj)
            seen_titles.add(item["title"])
            all_results.sort(key=lambda x: x["profit"], reverse=True)

            try:
                loop = asyncio.get_running_loop()
                loop.create_task(message_queue.put(json.dumps({"type": "new_result", "data": result_obj})))
            except RuntimeError:
                asyncio.run(message_queue.put(json.dumps({"type": "new_result", "data": result_obj})))

            return all_results

    query = parsed["query"]
    condition = parsed.get("condition", "any")
    include_terms = parsed.get("include_terms", [])
    exclude_terms = parsed.get("exclude_terms", [])

    all_results = []
    seen_titles = set()
    seen_queries = set()
    seen_queries.add((query.lower().strip(), condition.lower().strip()))

    def try_query(q, cond, includes, excludes):
        raw_items = run_ebay_search(q, cond, includes, excludes, postal_code)
        return filter_and_score(raw_items, includes, excludes)

    async def gpt_fallback_search(iteration_num, original_input, original_query, original_include_terms, original_exclude_terms, condition, seen_queries):
        prompt = f"""
You're helping refine a resale-related eBay search based on a user's original message.

User's full original search message:
\"{original_input}\"

Original parsed intent:
- Query: \"{original_query}\"
- Condition: {condition}
- Include terms: {json.dumps(original_include_terms)}
- Exclude terms: {json.dumps(original_exclude_terms)}

Please try a **new, independent** eBay-style search query:

- Do not copy the previous search query — instead, search something that is different yet fundamentally related to the original query.
- Reword the `query` to be simple and natural, but meaningfully different.
- The new query should **NEVER exceed 3–4 words (excluding brand names)**.
- 🔒 Always preserve the product *category* (e.g., “mixer” must stay a kitchen appliance — not a DJ mixer).
- 🔒 Keep the brand name (e.g., “kitchenaid”) or a close spelling unless the original query was generic.
- You may simplify or remove unnecessary words from the query and move them into `include_terms`.
- Do NOT ignore the user's intent — especially regarding condition or tolerance for flaws.
- 🛑 NEVER include unrelated categories (e.g., DJ mixer when searching for kitchen mixer).
- NEVER add unrelated words unless the user originally said so.

Return ONLY valid JSON in the exact format below:
{{
  "query": "short new search string",
  "condition": "{condition}",
  "include_terms": {json.dumps(original_include_terms)},
  "exclude_terms": {json.dumps(original_exclude_terms)}
}}
"""

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You help refine search criteria for resale flipping."},
                {"role": "user", "content": prompt}
            ]
        )
        raw = response.choices[0].message.content.strip()
        if raw.startswith("```json"):
            raw = raw.removeprefix("```json").strip()
        if raw.endswith("```"):
            raw = raw.removesuffix("```").strip()
        raw = re.sub(r",(\s*[}\]])", r"\1", raw)
        parsed_fallback = json.loads(raw)

        query = parsed_fallback["query"]
        cond = parsed_fallback["condition"]
        includes = parsed_fallback.get("include_terms", [])
        excludes = parsed_fallback.get("exclude_terms", [])

        query_key = (query.lower().strip(), cond.lower().strip())
        if query_key in seen_queries:
            print(f"⚠️ Iteration {iteration_num}: Duplicate combo, skipping.")
            return []
        seen_queries.add(query_key)

        results = run_ebay_search(query, cond, includes, excludes, postal_code)
        return results if results else []

    async def run_raw_query():
        try:
            return try_query(query, condition, include_terms, exclude_terms)
        except Exception as e:
            print("❌ Raw query failed:", e)
            return []

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    parallel_results = loop.run_until_complete(asyncio.gather(
    run_raw_query(),
    gpt_fallback_search(1, original_input, query, include_terms, exclude_terms, condition, seen_queries),
    gpt_fallback_search(2, original_input, query, include_terms, exclude_terms, condition, seen_queries)
    ))


    alt1_query = ""
    alt2_query = ""

    for idx, group in enumerate(parallel_results):
        if not group:
            continue

        async def calculate_all(items):
            loop = asyncio.get_event_loop()
            tasks = [loop.run_in_executor(None, calculate_profit, item, condition) for item in items]
            return await asyncio.gather(*tasks)

        results = loop.run_until_complete(calculate_all(group))

        for i, result in enumerate(results):
            if result is None:
                continue

            item = group[i]
            if item["title"] in seen_titles:
                continue

            total_price, profit_value, roi, item_price, shipping, refined_query, adjusted_condition, description = result

            result_obj = {
                "title": item.get("title"),
                "price": total_price,
                "item_price": item_price,
                "description": description,
                "shipping": shipping,
                "profit": profit_value,
                "roi": roi,
                "profit_color": "green",
                "thumbnail": item.get("image", {}).get("imageUrl"),
                "url": item.get("itemWebUrl"),
                "refined_query": refined_query,
                "adjusted_condition": adjusted_condition
            }

            all_results.append(result_obj)
            seen_titles.add(item["title"])
            all_results.sort(key=lambda x: x["profit"], reverse=True)

            try:
                loop.create_task(message_queue.put(json.dumps({"type": "new_result", "data": result_obj})))
            except RuntimeError:
                asyncio.run(message_queue.put(json.dumps({"type": "new_result", "data": result_obj})))

        if idx == 1 and group:
            alt1_query = group[0].get("title", "")
        elif idx == 2 and group:
            alt2_query = group[0].get("title", "")

        if len(all_results) >= 5 and all(item["roi"] >= ROI_THRESHOLD for item in sorted(all_results, key=lambda x: x["profit"], reverse=True)[:5]):
            return {
                "results": sorted(all_results, key=lambda x: x["profit"], reverse=True)[:5],
                "alt1": alt1_query,
                "alt2": alt2_query
            }

    return {
        "results": sorted(all_results, key=lambda x: x["profit"], reverse=True)[:5],
        "alt1": alt1_query,
        "alt2": alt2_query
    }

@app.post("/ai_search")
def ai_search(nq: NaturalQuery):
    log_event("Search", f"query={nq.search}, zip={nq.postalCode or 'N/A'}")
    try:
        parsed = {
            "query": nq.search,
            "condition": "any",
            "include_terms": [],
            "exclude_terms": []
        }
        print("🔍 Using raw input for initial query")


        # ✅ Pass ZIP to eBay search
        results = search_ebay(parsed, nq.search, nq.postalCode)

        return {
            "parsed": {
                **parsed,
                "alt1": results.get("alt1"),
                "alt2": results.get("alt2")
            },
            "results": results["results"],
            "qualified_count": len(results["results"])
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

from fastapi.responses import StreamingResponse

@app.get("/events")
async def sse_event_stream():
    async def event_generator():
        while True:
            message = await message_queue.get()
            yield f"data: {message}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

