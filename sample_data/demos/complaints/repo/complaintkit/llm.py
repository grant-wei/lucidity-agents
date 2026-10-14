"""One model call per complaint, cached on disk so an unchanged prompt is never paid for twice.

The cache lives in the repo's git directory (shared by every worktree, never committed). Calls that
miss it need OPENAI_API_KEY; usage is counted so the eval can report what it cost."""
import hashlib
import json
import os
import subprocess
import threading
from pathlib import Path

MODEL = os.environ.get("OPENAI_MODEL") or "gpt-6-luna"
PRICES = {"gpt-6-luna": (0.10, 0.01, 0.50)}  # USD per 1M tokens: input, cached input, output
ROOT = Path(__file__).resolve().parent.parent
usage = {"calls": 0, "cache_hits": 0, "input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0, "usd": 0.0}
_lock = threading.Lock()
_client = None


def cache_dir():
    try:
        common = subprocess.run(["git", "rev-parse", "--git-common-dir"], cwd=ROOT, capture_output=True,
                                text=True, timeout=30).stdout.strip()
    except OSError:
        common = ""
    base = (ROOT / common).resolve() if common else ROOT / ".cache"
    return base / "complaintkit-cache"


def _key(prompt):
    return hashlib.sha256(f"{MODEL}\n{prompt}".encode("utf-8")).hexdigest()


def complete(prompt):
    path = cache_dir() / f"{_key(prompt)}.json"
    if path.exists():
        with _lock:
            usage["cache_hits"] += 1
        return json.loads(path.read_text(encoding="utf-8"))["answer"]
    answer, u = _call(prompt)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"model": MODEL, "answer": answer}), encoding="utf-8")
    inp, cached, out = u
    price = PRICES.get(MODEL, (0, 0, 0))
    with _lock:
        usage["calls"] += 1
        usage["input_tokens"] += inp
        usage["cached_input_tokens"] += cached
        usage["output_tokens"] += out
        usage["usd"] += ((inp - cached) * price[0] + cached * price[1] + out * price[2]) / 1e6
    return answer


def _call(prompt):
    global _client
    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("this prompt has no cached answers and OPENAI_API_KEY is not set")
    if _client is None:
        from openai import OpenAI
        _client = OpenAI()
    r = _client.responses.create(model=MODEL, input=prompt, reasoning={"effort": "low"}, max_output_tokens=2000)
    cached = getattr(getattr(r.usage, "input_tokens_details", None), "cached_tokens", 0) or 0
    return r.output_text.strip(), (r.usage.input_tokens, cached, r.usage.output_tokens)
