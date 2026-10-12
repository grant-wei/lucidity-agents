"""Step 4 check: run the coordinator twice on sample data; print state vs label, tokens, and skips."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lucidity.agents.coordinator import Options, refresh  # noqa: E402

mode = sys.argv[1] if len(sys.argv) > 1 else "sample"
labels = json.loads((Path(__file__).resolve().parent.parent / "sample_data" / "labels.json").read_text(encoding="utf-8"))
for run in (1, 2):
    snap = refresh(Options(mode=mode))
    t = snap["trace"]
    print(f"\nrun {run}: changed={snap['changed']} skipped={snap['skipped']} tokens={t['tokens']} usd={t['usd']} secs={t['seconds']}")
    for n in t["nodes"]:
        if n["kind"] == "agent":
            print(f"  {n['label']}: tokens={n['tokens']} usd={n['usd']} tools={[x['name'] for x in n['tools']]}")
    if run == 1:
        for r in snap["sessions"]:
            exp = (labels.get(r["id"]) or {}).get("state", "?") if mode == "sample" else "?"
            chk = (r.get("checker") or {}).get("verdict", "")
            print(f"  {r['project']:<18} got={r['state']:<10} label={exp:<10} flags={[f['kind'] for f in r['flags']]} "
                  f"checker={chk} secrets={[x['kind'] for x in r['secrets']]} warn={'Y' if r['warning'] else ''} claims={len(r['claims'])} dropped={r['dropped_claims']}")
