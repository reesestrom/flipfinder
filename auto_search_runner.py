import os
import sys
import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from models import SessionLocal, SavedSearch, SearchResultSnapshot, User
from app import search_ebay, ksl_deals, NaturalQuery
import asyncio

db = SessionLocal()
now = datetime.datetime.utcnow()

print("🔁 Running auto-search snapshot runner...")


def run_snapshot_for_search(search, user):
    try:
        parsed = {
            "query": search.query_text,
            "condition": "any",
            "include_terms": [],
            "exclude_terms": []
        }

        # 🔹 eBay search
        ebay_results = search_ebay(parsed, search.query_text)
        ebay_top_5 = ebay_results["results"][:5] if ebay_results else []

        print(f"📦 {user.username} | eBay | {search.query_text} | {len(ebay_top_5)} results")

        for item in ebay_top_5:
            snapshot = SearchResultSnapshot(
                user_id=user.id,
                query_text=search.query_text,
                title=item["title"],
                url=item["url"],
                thumbnail=item.get("thumbnail"),
                price=item["price"],
                shipping=item["shipping"],
                profit=item["profit"],
                created_at=now,
                source="ebay"
            )
            db.add(snapshot)

        # 🔹 KSL search (run async inline)
        ksl_results = asyncio.run(ksl_deals(NaturalQuery(search=search.query_text)))
        ksl_top_5 = ksl_results["results"][:5] if ksl_results and "results" in ksl_results else []

        print(f"📦 {user.username} | KSL | {search.query_text} | {len(ksl_top_5)} results")

        for item in ksl_top_5:
            snapshot = SearchResultSnapshot(
                user_id=user.id,
                query_text=search.query_text,
                title=item["title"],
                url=item["url"],
                thumbnail=item.get("thumbnail"),
                price=item["price"],
                shipping=0,
                profit=item["profit"],
                created_at=now,
                source="ksl"
            )
            db.add(snapshot)

        db.commit()

    except Exception as e:
        print(f"❌ Error during snapshot for {user.username}: {e}")


# 🔁 Run for each search (sequentially)
searches = db.query(SavedSearch).filter_by(auto_search_enabled=True).all()
for search in searches:
    user = db.query(User).filter(User.id == search.user_id).first()
    if not user:
        continue
    run_snapshot_for_search(search, user)

db.close()
print("✅ Snapshot runner finished.")
