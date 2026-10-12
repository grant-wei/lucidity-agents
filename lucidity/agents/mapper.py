"""The map refresh: plain code builds the architecture map from every session's file edits, then
the architect agent describes only the repos whose file list changed since it last saw them.
Runs on its own thread so a slow first scan of a big repo never holds up the session cards."""
from .. import config
from ..guard import BudgetExceeded
from ..llm import ModelCallFailed
from ..readers import clock, map_sessions
from ..repomap import build
from ..trace import Trace
from . import architect

MAX_DESCRIBE_PER_REFRESH = 3   # a first run on many repos spreads its model calls over a few refreshes


def refresh_map(mode=None, use_model=True):
    mode = mode or config.DATA_MODE
    now = clock(mode)
    tr = Trace(mode)
    sessions = map_sessions(mode)
    m = build(sessions, mode, now)
    tr.node("mapper", "Map builder", "code",
            output=f"{len(m['repos'])} repos, {sum(r['edits'] for r in m['repos'])} file edits from {len(sessions)} sessions",
            note="git file list, import links and per-session edits; no model")
    cache = architect.load_cache()
    described, banner = 0, None
    for repo in m["repos"]:
        key = f"{mode}:{repo['name']}"
        hit = cache.get(key)
        if hit and hit.get("sig") == repo["sig"]:
            repo["architect"] = hit
            continue
        if hit:
            repo["architect"] = {**hit, "stale": True}   # last roles, until the new ones come in
        if not use_model or not config.has_key() or described >= MAX_DESCRIBE_PER_REFRESH or banner:
            continue
        nid = f"architect:{repo['name']}"
        tr.node(nid, f"Architect ({repo['name']})", "agent", parent="mapper", note="one role line per module")
        try:
            roles, row, prompt = architect.describe(repo, trace=tr, node_id=nid, refresh_id=tr.id)
        except BudgetExceeded as e:
            banner = f"Lucidity paused its own model calls: {e}. The map shows modules without roles."
            continue
        except ModelCallFailed as e:
            tr.charge(nid, e.row)
            tr.get(nid)["output"] = f"Model call failed: {str(e)[:200]}. Tries again next refresh."
            described += 1
            continue
        described += 1
        tr.charge(nid, row)
        tr.get(nid)["input"] = prompt[:6000]
        tr.get(nid)["output"] = f"{len(roles['roles'])} roles kept, {roles['dropped']} dropped"
        cache[key] = {**roles, "sig": repo["sig"]}
        repo["architect"] = cache[key]
    architect.save_cache(cache)
    if described:
        tr.save()
    return {**m, "mode": mode, "now": now.isoformat(), "banner": banner, "trace_id": tr.id if described else None}
