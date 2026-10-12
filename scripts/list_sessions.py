"""Print the most recent sessions as a table, no prompt text."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lucidity.readers import load_sessions  # noqa: E402

mode = sys.argv[1] if len(sys.argv) > 1 else "sample"
rows = load_sessions(mode, limit=15)
print(f"{'tool':6} {'project':22} {'last activity':20} {'events':>6} {'tokens':>12} {'$':>8}  open/pending  scenario")
for s in rows[:15]:
    tok = s.tokens["input"] + s.tokens["output"]
    flag = "Q" if s.pending_question else (s.open_tool_call or "")
    print(f"{s.tool:6} {s.project[:22]:22} {(s.last_activity or '')[:19]:20} {s.event_count:>6} {tok:>12,} {s.usd:>8.2f}  {flag[:12]:12}  {s.scenario or ''}")
