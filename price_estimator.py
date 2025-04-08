import statistics
import requests
import os
import base64
from dotenv import load_dotenv

load_dotenv()

EBAY_CLIENT_ID = os.getenv("EBAY_CLIENT_ID", "")
EBAY_CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET", "")
EBAY_OAUTH_TOKEN = None
EBAY_TOKEN_EXPIRY = 0

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
        raise Exception("Failed to refresh eBay token")

    token_data = response.json()
    EBAY_OAUTH_TOKEN = token_data["access_token"]
    EBAY_TOKEN_EXPIRY = time.time() + int(token_data["expires_in"])
    return EBAY_OAUTH_TOKEN


def refined_avg_price(query, condition=None):
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    headers = {
        "Authorization": f"Bearer {get_ebay_token()}",
        "Content-Type": "application/json",
    }

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
