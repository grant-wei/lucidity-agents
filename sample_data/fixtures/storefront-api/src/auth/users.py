"""User lookup."""
from sqlalchemy import select
from db.models import User
from db.session import db


def find_by_email(email):
    return db.scalar(select(User).where(User.email == email))
