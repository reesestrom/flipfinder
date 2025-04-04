from sqlalchemy import Column, Integer, Boolean, String, DateTime, Float, ForeignKey, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from passlib.context import CryptContext
import datetime
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
load_dotenv()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password)

    def set_password(self, password: str):
        self.hashed_password = pwd_context.hash(password)


class SavedItem(Base):
    __tablename__ = "saved_items"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    price = Column(Float)
    profit = Column(Float)
    url = Column(String)
    thumbnail = Column(String)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class SavedSearch(Base):
    __tablename__ = "saved_searches"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    query_text = Column(String)
    auto_search_enabled = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_run = Column(DateTime, nullable=True)


class SearchResultSnapshot(Base):
    __tablename__ = "search_result_snapshots"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    query_text = Column(String)
    title = Column(String)
    url = Column(String)
    thumbnail = Column(String)
    price = Column(Float)
    shipping = Column(Float)
    profit = Column(Float)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


# ✅ New model to track emailed snapshots and prevent re-sending
class EmailedListing(Base):
    __tablename__ = "emailed_listings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    url = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


Base.metadata.create_all(bind=engine)
