"""Lucidity's own circuit breaker: a daily dollar cap and a calls-per-hour cap on its
own model use. It reads logs/usage.jsonl, so the limit holds across restarts."""
import json
from datetime import datetime, timedelta, timezone

from . import config


class BudgetExceeded(RuntimeError):
    pass


class Breaker:
    def __init__(self):
        self.daily_usd_cap = config.DAILY_USD_CAP
        self.calls_per_hour_cap = config.CALLS_PER_HOUR_CAP
        self.tripped = None  # reason string once tripped

    def _rows(self):
        path = config.LOG_DIR / "usage.jsonl"
        if not path.exists():
            return []
        rows = []
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
        return rows

    def status(self):
        now = datetime.now(timezone.utc)
        today = now.date().isoformat()
        hour_ago = (now - timedelta(hours=1)).isoformat(timespec="seconds")
        rows = self._rows()
        spent = sum(r.get("usd", 0) for r in rows if r.get("ts", "").startswith(today))
        calls = sum(r.get("requests", 1) for r in rows if r.get("ts", "") >= hour_ago)
        reason = None
        if spent >= self.daily_usd_cap:
            reason = f"daily cap reached: ${spent:.4f} of ${self.daily_usd_cap:.2f}"
        elif calls >= self.calls_per_hour_cap:
            reason = f"call rate cap reached: {calls} model requests in the last hour (cap {self.calls_per_hour_cap})"
        return {"usd_today": round(spent, 6), "calls_last_hour": calls, "daily_usd_cap": self.daily_usd_cap,
                "calls_per_hour_cap": self.calls_per_hour_cap, "tripped": reason,
                "calls_today": sum(r.get("requests", 1) for r in rows if r.get("ts", "").startswith(today)),
                "tokens_today": sum((r.get("input_tokens") or 0) + (r.get("output_tokens") or 0)
                                    for r in rows if r.get("ts", "").startswith(today))}

    def check(self):
        reason = self.status()["tripped"]
        self.tripped = reason
        if reason:
            raise BudgetExceeded(reason)

    def record(self, row):
        pass  # the log is the record; status() rereads it


breaker = Breaker()
