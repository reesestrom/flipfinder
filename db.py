from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import Base
import os

# ✅ Load the DATABASE_URL from environment variables (.env file or Render)
DATABASE_URL = os.getenv("DATABASE_URL")

# ✅ Create the engine and session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ This function provides a database session to route functions
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
