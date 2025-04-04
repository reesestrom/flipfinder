import os
import sys
import datetime
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from models import SessionLocal, SavedSearch, SearchResultSnapshot, User
from app import parse_search_criteria, search_ebay

db = SessionLocal()
now = datetime.datetime.utcnow()

print("🔁 Running auto-search snapshot runner...")

searches = db.query(SavedSearch).filter_by(auto_search_enabled=True).all()
for search in searches:
    user = db.query(User).filter(User.id == search.user_id).first()
    if not user:
        continue

    try:
        parsed = parse_search_criteria(search.query_text)
        results = search_ebay(parsed, search.query_text)
        top_5 = results[:5]

        print(f"📦 {user.username} | {search.query_text} | {len(top_5)} results")

        for item in top_5:
            snapshot = SearchResultSnapshot(
                user_id=user.id,
                query_text=search.query_text,
                title=item["title"],
                url=item["url"],
                thumbnail=item.get("thumbnail"),
                price=item["price"],
                shipping=item["shipping"],
                profit=item["profit"],
                created_at=now
            )
            db.add(snapshot)
        db.commit()

    except Exception as e:
        print(f"❌ Error during snapshot: {e}")

db.close()
print("✅ Snapshot runner finished.")
