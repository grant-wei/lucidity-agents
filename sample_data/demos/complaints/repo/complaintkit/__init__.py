"""Routes a consumer's complaint to the product team that handles it."""
from .route import LABELS, route, route_many

__all__ = ["LABELS", "route", "route_many"]
