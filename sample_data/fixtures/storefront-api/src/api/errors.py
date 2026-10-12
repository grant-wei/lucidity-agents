"""JSON error responses."""


def error(status, message):
    return status, {"error": message}
