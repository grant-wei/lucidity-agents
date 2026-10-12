"""Settings, read once. The .env lookup order is the course rule: repo folder, then the folder above."""
import os
from pathlib import Path

from dotenv import load_dotenv

os.environ.setdefault("PYDANTIC_AI_NO_BANNER", "1")

ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = ROOT / "logs"
SAMPLE_DIR = ROOT / "sample_data"
STATE_DIR = ROOT / "state"


def _load_env():
    for folder in (ROOT, ROOT.parent):
        path = folder / ".env"
        if path.exists():
            load_dotenv(path, override=False)
            return path
    return None


ENV_PATH = _load_env()
MODEL = os.environ.get("OPENAI_MODEL") or "gpt-6-luna"
DATA_MODE = (os.environ.get("LUCIDITY_DATA") or "sample").lower()  # sample | local
PORT = int(os.environ.get("LUCIDITY_PORT") or 8765)

# Lucidity's own spending limits. These exist because the first version of this
# tool ran away (about 1,750 model calls an hour for three days) before anyone noticed.
DAILY_USD_CAP = float(os.environ.get("LUCIDITY_DAILY_USD_CAP") or 0.50)
CALLS_PER_HOUR_CAP = int(os.environ.get("LUCIDITY_CALLS_PER_HOUR_CAP") or 120)
REFRESH_SECONDS = int(os.environ.get("LUCIDITY_REFRESH_SECONDS") or 60)


def has_key():
    return bool(os.environ.get("OPENAI_API_KEY"))
