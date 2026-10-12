"""Database engine and session (SQLAlchemy 2)."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

engine = create_engine("sqlite:///store.db")
db = Session(engine)
