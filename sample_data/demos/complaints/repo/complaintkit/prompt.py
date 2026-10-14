"""The prompt sent to the model for each complaint."""

PROMPT = """Read this customer complaint and say which financial product it is about.

Complaint:
{text}"""


def build(text):
    return PROMPT.format(text=text)
