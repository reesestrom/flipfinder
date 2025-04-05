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
from sqlalchemy.orm import Session

app = FastAPI()

app.include_router(reset_router)
app.include_router(auto_search_bp)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://flipfinderwebsite.onrender.com",  # production frontend
        "http://localhost:3000",                   # local React dev
        "http://127.0.0.1:3000",                   # fallback local
        "null"                                     # file:// access during local dev
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

@app.post("/set_email_days")
def set_email_days(data: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    current_user.email_days = ",".join(str(day) for day in data["days"])
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
        raise HTTPException(status_code=404, detail="User not found")

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
    email = data.get("email")
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # delete related data
    db.query(AutoSearch).filter(AutoSearch.user_id == user.id).delete()
    db.query(SavedSearch).filter(SavedSearch.user_id == user.id).delete()
    db.query(Snapshot).filter(Snapshot.user_id == user.id).delete()
    db.query(EmailedSnapshot).filter(EmailedSnapshot.user_id == user.id).delete()
    db.delete(user)
    db.commit()

    return {"message": "Account deleted"}

@app.get("/get_email/{username}")
def get_email(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {"email": user.email}


@app.get("/get_email_days/{username}")
def get_email_days(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.email_days:
        return {"days": [0,1,2,3,4,5,6]}  # default to all days selected

    return {"days": [int(d) for d in user.email_days.split(",") if d.isdigit()]}


@auto_search_bp.post("/disable_auto_search")
def disable_auto_search(data: dict = Body(...), db: Session = Depends(get_db)):
    username = data.get("username")
    query_text = data.get("query_text")

    if not username or not query_text:
        raise HTTPException(status_code=400, detail="Missing username or query_text")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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
        raise HTTPException(status_code=404, detail="User not found")

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

@app.post("/unsave_item")
def unsave_item(data: dict = Body(...), db: Session = Depends(get_db)):
    username = data.get("username")
    item = data.get("item")

    if not username or not item:
        raise HTTPException(status_code=400, detail="Missing username or item")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Delete saved item by URL
    deleted = db.query(SavedItem).filter_by(user_id=user.id, url=item["url"]).delete()
    db.commit()

    return {"message": "Item unsaved", "deleted_count": deleted}


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
@app.get("/saved_searches/{username}")
def get_saved_searches(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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

class NaturalQuery(BaseModel):
    search: str
    postalCode: str | None = None  # ✅ Add this line

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
        "limit": "25"
    }
    if filter_str:
        params["filter"] = filter_str

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        return 0

    data = response.json()
    items = data.get("itemSummaries", [])
    prices = [float(item["price"]["value"]) for item in items if "price" in item]
    return sum(prices) / len(prices) if prices else -999


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

        import re  # ✅ Add this at the top of the file
        params = {
            "q": query,
            "limit": "80",
        }
        # ✅ Add only if ZIP is valid 5-digit number
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
            return None  # ❌ No shipping info at all

        for option in shipping_options:
            shipping_type = option.get("shippingType", "").lower()

            # ✅ We're only interested in actual shipping options (not just pickup)
            if "pickup" in shipping_type:
                continue  # Skip pickup-only lines, but keep looking

            cost_data = option.get("shippingCost", {})

            # ✅ Accept both free and paid shipping
            if cost_data is not None and "value" in cost_data:
                cost = float(cost_data["value"])
                print(f"✅ Found shipping: ${cost:.2f} for {item.get('title')}")
                return cost

        # ❌ If we got here, then there were no valid shipping options (only pickup or junk)
        print(f"❌ Only pickup found — skipping: {item.get('title')}")
        return None



    def calculate_profit(item, parsed_condition):
        def safe_enqueue_increment():
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(message_queue.put("increment"))
            except RuntimeError:
                asyncio.run(message_queue.put("increment"))

        for _ in range(26):
            safe_enqueue_increment()

        price = float(item.get("price", {}).get("value", 0))
        shipping = extract_shipping_cost(item)

        if shipping is None:
            return None  # ✅ skip item if shipping not usable

        total_price = price + shipping

        # ✅ NEW: Fetch full item details for actual description
        item_id = item.get("itemId", "")
        full_item = fetch_item_details(item_id)
        description = full_item.get("description", "")

        title = item.get("title", "")
        refinement = refine_title_and_condition(title, description, parsed_condition)

        refined_query = refinement["refined_query"]
        adjusted_condition = refinement["adjusted_condition"]

        refined_resale = refined_avg_price(refined_query, adjusted_condition)

        profit = (refined_resale * 0.85) - total_price
        roi = round(profit / total_price, 2) if total_price > 0 else 0

        return total_price, profit, roi, price, shipping, refined_query, adjusted_condition, description

    

    def filter_and_score(items, include_terms, exclude_terms):
        filtered = []
        for item in items:
            title = item.get("title", "").lower()

            if any(term.lower() in title for term in exclude_terms):
                continue
            if not all(term.lower() in title for term in include_terms):
                continue

            result = calculate_profit(item, condition)
            if result is None:
                continue  # ❌ skip bad shipping items

            total_price, profit_value, roi, item_price, shipping, refined_query, adjusted_condition, description = result


            if shipping is None:
                continue  # ✅ Skip if no usable shipping info
            if profit_value <= 0:
                continue

            filtered.append({
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
            })

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
        raw_items = run_ebay_search(q, cond, includes, excludes, postal_code)
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
- Be flexible and change any included and excluded terms, but make sure they are still connected to or relevant to the original search query. For example, use synonyms (changing "broken" to "not working")
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
    log_event("Search", f"query={nq.search}, zip={nq.postalCode or 'N/A'}")
    try:
        parsed = parse_search_criteria(nq.search)
        print("🔍 AI INTERPRETATION:")
        print(json.dumps(parsed, indent=2))

        # ✅ Pass ZIP to eBay search
        results = search_ebay(parsed, nq.search, postal_code=nq.postalCode)

        # ✅ Count ROI-qualified items (ROI >= 0.5)
        qualified_count = sum(1 for item in results if item.get("roi", 0) >= 0.5)

        return {
            "parsed": parsed,
            "results": results,
            "qualified_count": qualified_count
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

