from fastapi import APIRouter, HTTPException, Depends, Body
from sqlalchemy.orm import Session
from models import SessionLocal, SavedSearch, SearchResultSnapshot, User
from datetime import datetime

auto_search_bp = APIRouter()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@auto_search_bp.get("/debug_saved_searches/{username}")
def debug_saved_searches(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    searches = db.query(SavedSearch).filter_by(user_id=user.id).all()
    return [
        {"query_text": s.query_text, "auto_search_enabled": s.auto_search_enabled}
        for s in searches
    ]


@auto_search_bp.post("/enable_auto_search")
def enable_auto_search(data: dict = Body(...), db: Session = Depends(get_db)):
    username = data.get("username")
    query_text = data.get("query_text")

    if not username or not query_text:
        raise HTTPException(status_code=400, detail="Missing username or query_text")

    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check current auto-search count
    active_count = db.query(SavedSearch).filter_by(user_id=user.id, auto_search_enabled=True).count()
    if active_count >= 3:
        raise HTTPException(status_code=403, detail="Max 3 auto-searches allowed")

    # Check if already exists
    existing = db.query(SavedSearch).filter_by(user_id=user.id, query_text=query_text).first()
    if existing:
        existing.auto_search_enabled = True
        db.commit()
        return {"message": "Auto-search enabled on existing saved search"}

    new_search = SavedSearch(
        user_id=user.id,
        query_text=query_text,
        auto_search_enabled=True,
        created_at=datetime.utcnow()
    )
    db.add(new_search)
    db.commit()
    return {"message": "Auto-search created and enabled"}

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

@auto_search_bp.get("/user_auto_searches/{username}")
def get_user_auto_searches(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    searches = db.query(SavedSearch).filter_by(user_id=user.id).all()
    return [
        {
            "query_text": s.query_text,
            "auto_search_enabled": s.auto_search_enabled,
            "created_at": s.created_at.isoformat(),
            "last_run": s.last_run.isoformat() if s.last_run else None
        }
        for s in searches
    ]
