"""Coordinator: mostly plain code. Reads every session, skips the ones whose change signature
hasn't moved since the last refresh, sends the rest to triage in one batched call, runs the
watchdog's detectors, asks the watchdog to explain only new flags, and asks the checker to
verify only sessions that newly claim to be finished and have a task contract.

The signature skip is the fix for the bug that started this project: an earlier version
re-summarized every session on every poll and made ~1,750 model calls an hour."""
import hashlib
import json
from dataclasses import dataclass

from .. import config
from ..guard import BudgetExceeded, breaker
from ..llm import ModelCallFailed
from ..readers import age_minutes, clock, load_sessions
from ..redact import redact, session_secrets
from ..trace import Trace
from . import checker, triage, watchdog


@dataclass
class Options:
    mode: str = None
    tail: int = 14            # events per session sent to triage
    batch: bool = True        # changed sessions share triage calls
    batch_size: int = 10      # sessions per triage call when batching
    skip_unchanged: bool = True
    run_checker: bool = True
    cache_name: str = None    # evals use their own cache


def signature(s, now):
    """What triage depends on, minus the clock (except for 'has it been sitting a while')."""
    last = s.events[-1] if s.events else None
    idle = age_minutes(s.last_activity, now) or 0
    parts = [s.id, str(s.event_count), last.id if last else "", (last.text[:200] if last else ""),
             s.pending_question or "", s.open_tool_call or "", str(idle > 3), str(idle > 30)]
    return hashlib.sha1("\x1f".join(parts).encode("utf-8", "replace")).hexdigest()[:16]


def _cache_path(opts):
    name = opts.cache_name or f"cache_{opts.mode}"
    return config.STATE_DIR / f"{name}.json"


def _load_cache(opts):
    p = _cache_path(opts)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except ValueError:
            return {}
    return {}


def _save_cache(opts, cache):
    config.STATE_DIR.mkdir(exist_ok=True)
    _cache_path(opts).write_text(json.dumps(cache, indent=1), encoding="utf-8")


def refresh(opts=None, sessions=None):
    opts = opts or Options()
    opts.mode = opts.mode or config.DATA_MODE
    now = clock(opts.mode)
    tr = Trace(opts.mode)
    sessions = sessions if sessions is not None else load_sessions(opts.mode)
    tr.node("collector", "Collector", "code",
            output=f"{len(sessions)} sessions read", note="reads transcripts, counts tokens and cost; no model")
    cache = _load_cache(opts)
    changed, skipped = [], []
    sigs = {}
    for s in sessions:
        sigs[s.id] = signature(s, now)
        hit = cache.get(s.id)
        if opts.skip_unchanged and hit and hit.get("sig") == sigs[s.id] and hit.get("triage"):
            skipped.append(s)
        else:
            changed.append(s)
    tr.node("coordinator", "Coordinator", "code", parent="collector",
            output=f"{len(changed)} changed, {len(skipped)} unchanged (skipped)",
            note="change signature per session; only changed sessions reach a model")
    banner = None
    usage_rows = []
    try:
        # triage
        if changed:
            size = opts.batch_size if opts.batch else 1
            groups = [changed[i:i + size] for i in range(0, len(changed), size)]
            for gi, group in enumerate(groups):
                nid = "triage" if gi == 0 else f"triage{gi + 1}"
                label = f"Triage ({group[0].project})" if len(group) == 1 else "Triage agent" + (f" {gi + 1}" if gi else "")
                tr.node(nid, label, "agent",
                        parent="coordinator", note=f"{len(group)} session(s) in one call")
                try:
                    results, row, prompt = triage.triage(group, now, trace=tr, node_id=nid, tail=opts.tail, refresh_id=tr.id)
                except ModelCallFailed as e:
                    _failed(tr, nid, e, usage_rows, "these sessions keep their last result and are read again next refresh")
                    continue
                tr.charge(nid, row)
                usage_rows.append(row)
                tr.get(nid)["input"] = prompt[:6000]
                tr.get(nid)["output"] = json.dumps(results, indent=1)[:6000]
                for sid, r in results.items():
                    cache.setdefault(sid, {})
                    cache[sid].update({"sig": sigs[sid], "triage": r})
        # watchdog: detectors on everything (free), model only on new flags
        flagged, explain_needed = [], []
        for s in sessions:
            flags = watchdog.detect(s, now)
            entry = cache.setdefault(s.id, {})
            entry["secrets"] = session_secrets(s)
            prev_flags = entry.get("flags_sig")
            entry["flags"] = flags
            if flags:
                flagged.append((s, flags))
                fsig = json.dumps([f["kind"] for f in flags]) + sigs[s.id]
                if fsig != prev_flags or not opts.skip_unchanged:
                    explain_needed.append((s, flags, fsig))
            else:
                entry.pop("explanation", None)
                entry["flags_sig"] = None
        tr.node("detectors", "Watchdog detectors", "code", parent="coordinator",
                output=f"{len(flagged)} flagged: " + ", ".join(f"{s.project} ({f[0]['kind']})" for s, f in flagged)
                + f"; secrets seen in {sum(1 for s in sessions if cache[s.id].get('secrets'))} session(s)",
                note=f"repeat >= {watchdog.REPEAT_CALLS}, rate >= {watchdog.CALLS_PER_MIN}/min, "
                     f"${watchdog.SESSION_USD_CAP:.0f}/session, same failure x{watchdog.SAME_FAILURE}")
        if explain_needed:
            tr.node("watchdog", "Watchdog agent", "agent", parent="detectors",
                    note=f"explains {len(explain_needed)} flagged session(s)")
            # one attempt per flag change: a session the model left out (or a failed call) is not re-asked every refresh
            for s, _, fsig in explain_needed:
                cache[s.id]["flags_sig"] = fsig
            try:
                exps, row, prompt = watchdog.explain([(s, f) for s, f, _ in explain_needed], now, trace=tr, refresh_id=tr.id)
            except ModelCallFailed as e:
                _failed(tr, "watchdog", e, usage_rows, "the flags still show; only the explanation is missing")
                exps, row, prompt = {}, None, None
        if explain_needed and row is not None:
            tr.charge("watchdog", row)
            usage_rows.append(row)
            tr.get("watchdog")["input"] = prompt[:6000]
            tr.get("watchdog")["output"] = json.dumps(exps, indent=1)[:6000]
            for sid, e in exps.items():
                cache.setdefault(sid, {})["explanation"] = e
        # checker: sessions that newly say they're finished and have a contract
        if opts.run_checker:
            tasks = checker.load_tasks()
            for s in sessions:
                entry = cache.get(s.id) or {}
                task = tasks.get(s.id)
                if not task or (entry.get("triage") or {}).get("state") != "finished":
                    continue
                if (entry.get("checker") or entry.get("checker_failed")) and entry.get("checker_sig") == sigs[s.id]                         and opts.skip_unchanged:
                    continue
                nid = f"checker:{s.id[:8]}"
                tr.node(nid, f"Done checker ({s.project})", "agent", parent="triage" if tr.get("triage") else "coordinator",
                        note="runs the task's tests, grades against done-when")
                entry["checker_sig"] = sigs[s.id]
                cache[s.id] = entry
                try:
                    verdict, row, prompt = checker.check(s, task, trace=tr, node_id=nid, refresh_id=tr.id)
                except ModelCallFailed as e:
                    _failed(tr, nid, e, usage_rows, "no verdict this time; it runs again when the session changes")
                    entry["checker_failed"] = True
                    continue
                entry.pop("checker_failed", None)
                tr.charge(nid, row)
                usage_rows.append(row)
                tr.get(nid)["input"] = prompt[:6000]
                tr.get(nid)["output"] = json.dumps(verdict, indent=1)[:6000]
                entry["checker"] = verdict
                entry["checker_sig"] = sigs[s.id]
                cache[s.id] = entry
    except BudgetExceeded as e:
        banner = f"Lucidity paused its own model calls: {e}. Showing the last results it had."
        tr.node("breaker", "Budget breaker", "code", parent="coordinator", output=str(e),
                note="Lucidity's own spending cap tripped; no model call was made")
    _save_cache(opts, cache)
    tr.save()
    return build_snapshot(sessions, cache, now, tr, banner, opts, len(changed), len(skipped))


def _failed(tr, nid, e, usage_rows, consequence):
    tr.charge(nid, e.row)
    usage_rows.append(e.row)
    tr.get(nid)["output"] = f"Model call failed: {str(e)[:200]}. {consequence[0].upper()}{consequence[1:]}."


def build_snapshot(sessions, cache, now, tr, banner, opts, n_changed, n_skipped):
    rows = []
    for s in sessions:
        entry = cache.get(s.id) or {}
        t = entry.get("triage") or triage.no_result(s, now)
        rows.append({
            "id": s.id, "tool": s.tool, "project": s.project or "(unknown)", "model": s.model,
            "first_prompt": redact(s.first_prompt), "scenario": s.scenario,
            "last_activity": s.last_activity, "idle_min": round(age_minutes(s.last_activity, now) or 0, 1),
            "tokens": s.tokens, "usd": s.usd, "event_count": s.event_count,
            "state": t.get("state"), "claims": t.get("claims", []), "warning": t.get("warning", ""),
            "dropped_claims": t.get("dropped_claims", 0), "overridden": t.get("overridden"),
            "flags": entry.get("flags") or [], "explanation": entry.get("explanation"),
            "checker": entry.get("checker"), "secrets": entry.get("secrets") or [],
            # the browser gets redacted text too: a screenshot of the log panel must not leak a key
            "events": [{k: redact(v) if isinstance(v, str) else v for k, v in e.__dict__.items()}
                       for e in s.events[-30:]],
        })
    order = {"needs_you": 0, "working": 1, "unknown": 2, "finished": 3}
    rows.sort(key=lambda r: (0 if r["flags"] else 1, order.get(r["state"], 2), r["idle_min"]))
    return {
        "mode": opts.mode, "now": now.isoformat(), "refresh_id": tr.id,
        "changed": n_changed, "skipped": n_skipped,
        "sessions": rows, "banner": banner or (breaker.status().get("tripped") and
                                              f"Lucidity's own budget cap is reached: {breaker.status()['tripped']}"),
        "self_cost": breaker.status(), "trace": tr.to_dict(),
    }
