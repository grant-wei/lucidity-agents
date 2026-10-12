"""Password login and session tokens."""
from .ratelimit import allow
from .users import find_by_email
from .tokens import issue


def login(request):
    if not allow(request.ip):
        return 429, {"error": "too many attempts"}
    user = find_by_email(request.json["email"])
    if not user or not user.check(request.json["password"]):
        return 401, {"error": "bad credentials"}
    return 200, {"token": issue(user)}
