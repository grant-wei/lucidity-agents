"""Entry point: builds the HTTP app and mounts the routes."""
from api.routes import ROUTES
from db.session import engine


def create_app():
    return {"routes": ROUTES, "engine": engine}
