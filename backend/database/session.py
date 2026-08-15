"""Application database engine/session factory."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def get_database_url():
    url=os.environ.get("DATABASE_URL")
    if not url: raise RuntimeError("DATABASE_URL is required")
    return url

def create_session_factory(database_url=None,echo=False):
    engine=create_engine(database_url or get_database_url(),pool_pre_ping=True,echo=echo)
    return sessionmaker(bind=engine,expire_on_commit=False)
