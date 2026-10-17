"""Settings, read once. The .env lookup order is the course rule: repo folder, then the folder above."""
import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
SAMPLE_DIR = ROOT / "sample_data"
STATE_DIR = ROOT / "state"


PLACEHOLDER_KEY = "your-openai-key-here"


def _real_key(value):
    value = (value or "").strip().strip("'\"")
    return bool(value) and value != PLACEHOLDER_KEY


def _load_env():
    # A copied .env.example in the repo still holds the placeholder key; skip it so a real
    # .env one folder up (where the course staff keep theirs) is used instead.
    for folder in (ROOT, ROOT.parent):
        path = folder / ".env"
        if path.exists() and _real_key(dotenv_values(path).get("OPENAI_API_KEY")):
            load_dotenv(path, override=False)
            return path
    return None


ENV_PATH = _load_env()
# LUCIDITY_MODEL=claude-haiku-5-5 (or any claude-*) runs on ANTHROPIC_API_KEY instead of OpenAI.
MODEL = os.environ.get("LUCIDITY_MODEL") or os.environ.get("OPENAI_MODEL") or "gpt-6-luna"
CLAUDE = MODEL.startswith("claude")
KEY_NAME = "ANTHROPIC_API_KEY" if CLAUDE else "OPENAI_API_KEY"
DATA_MODE = (os.environ.get("LUCIDITY_DATA") or "sample").lower()  # sample | local
PORT = int(os.environ.get("LUCIDITY_PORT") or 8765)
# Hosted on a public server (grantwei.com/lucidity): listen on every interface, and let visitors use only
# the demos and tables they upload, never a folder or file path on the machine.
# The address prefix when served under another site, e.g. "/lucidity" for grantwei.com/lucidity.
BASE = "/" + (os.environ.get("LUCIDITY_BASE") or "").strip().strip("/") if (os.environ.get("LUCIDITY_BASE") or "").strip("/ ") else ""
HOSTED = (os.environ.get("LUCIDITY_HOSTED") or "").strip().lower() in ("1", "true", "yes")

# Lucidity's own spending limits. These exist because the first version of this
# tool ran away (about 1,750 model calls an hour for three days) before anyone noticed.
DAILY_USD_CAP = float(os.environ.get("LUCIDITY_DAILY_USD_CAP") or 0.50)
CALLS_PER_HOUR_CAP = int(os.environ.get("LUCIDITY_CALLS_PER_HOUR_CAP") or 600)
REFRESH_SECONDS = int(os.environ.get("LUCIDITY_REFRESH_SECONDS") or 60)
# The most one orchestrator run may be budgeted, whatever the page asks for. A run stops
# starting tasks at its own budget; each task stops at its share and waits for you.
MAX_RUN_USD = float(os.environ.get("LUCIDITY_MAX_RUN_USD") or 5.0)


# Hosted: the key arrives in a file that is read once and deleted, and it never sits in the process
# environment, so code the agents write and run can't read it from there.
_KEY_FILE = os.environ.pop("LUCIDITY_KEY_FILE", "")
_KEY = None
if _KEY_FILE:
    try:
        _KEY = Path(_KEY_FILE).read_text(encoding="utf-8").strip() or None
        Path(_KEY_FILE).unlink()
    except OSError:
        pass


def api_key():
    return _KEY or os.environ.get(KEY_NAME)


def has_key():
    return _real_key(api_key())
