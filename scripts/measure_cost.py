"""Step 14: measure what a refresh costs and write docs/evidence/numbers.json.

Runs one cold refresh (empty cache) and 3 warm refreshes on the sample data, then scales to
per-user-per-month at 100 and 10,000 users. The refresh rate per user comes from the pilot; until the
pilot has run it stays a [MISSING] marker and the scaled figures are shown for an assumed rate, labeled as such.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from lucidity import config  # noqa: E402
from lucidity.agents.coordinator import Options, refresh  # noqa: E402

OUT = ROOT / "docs" / "evidence" / "numbers.json"
CACHE = "measure_cost"
WARM = 3

# Set from the pilot: changed-session refreshes per user per working day. None until measured.
PILOT_CHANGED_REFRESHES_PER_DAY = None
ASSUMED_CHANGED_REFRESHES_PER_DAY = 40   # only for the labeled "assumed" row
WORKDAYS_PER_MONTH = 21


def run(opts):
    snap = refresh(opts)
    t = snap["trace"]
    reqs = sum(1 for n in t["nodes"] if n["kind"] == "agent")
    return {"changed": snap["changed"], "skipped": snap["skipped"], "model_calls": reqs,
            "tokens": t["tokens"], "usd": t["usd"], "seconds": t["seconds"]}


def scale(usd_per_changed_refresh, per_day):
    month = usd_per_changed_refresh * per_day * WORKDAYS_PER_MONTH
    return {"per_user_per_month_usd": round(month, 4), "users_100_usd": round(month * 100, 2),
            "users_10000_usd": round(month * 10_000, 2)}


def main():
    (config.STATE_DIR / f"{CACHE}.json").unlink(missing_ok=True)
    cold_with_checker = run(Options(mode="sample", cache_name=CACHE, run_checker=True))
    (config.STATE_DIR / f"{CACHE}.json").unlink(missing_ok=True)
    cold = run(Options(mode="sample", cache_name=CACHE, run_checker=False))
    warm = [run(Options(mode="sample", cache_name=CACHE, run_checker=False)) for _ in range(WARM)]
    # A changed session costs roughly cold cost / sessions read; per-user cost scales with how many change.
    per_session = cold["usd"] / max(cold["changed"], 1)

    evals = json.loads((ROOT / "evals" / "results.json").read_text(encoding="utf-8"))
    out = {
        "measured_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": config.MODEL,
        "source": "scripts/measure_cost.py on the 8 sample sessions. cold_refresh_as_the_app_runs_it includes the done checker; "
                  "the other rows leave it off, since it runs only when a session claims done and scaling uses triage cost",
        "cold_refresh_as_the_app_runs_it": cold_with_checker,
        "cold_refresh": cold,
        "warm_refreshes": warm,
        "usd_per_changed_session": round(per_session, 6),
        "pilot_changed_sessions_per_day": PILOT_CHANGED_REFRESHES_PER_DAY
        if PILOT_CHANGED_REFRESHES_PER_DAY is not None else "[MISSING: from the pilot]",
        "scaled_from_pilot": scale(per_session, PILOT_CHANGED_REFRESHES_PER_DAY)
        if PILOT_CHANGED_REFRESHES_PER_DAY is not None else "[MISSING: needs the pilot rate]",
        "scaled_assumed": {"assumption": f"{ASSUMED_CHANGED_REFRESHES_PER_DAY} changed sessions read per user per "
                           f"working day, {WORKDAYS_PER_MONTH} days a month. Not measured.",
                           **scale(per_session, ASSUMED_CHANGED_REFRESHES_PER_DAY)},
        "evals": {"ran_at": evals.get("ran_at"), "summary": evals.get("summary"),
                  "configs": evals.get("configs")},
        "daily_cap_usd": config.DAILY_USD_CAP,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("cold_refresh_as_the_app_runs_it", "cold_refresh", "warm_refreshes", "usd_per_changed_session",
                                          "scaled_assumed")}, indent=2))


if __name__ == "__main__":
    main()
