"""The repo map for a run: the repo split into modules (plain code, see repomap.py), with each
module marked by the tasks whose files landed in it. Read from the run's integration worktree,
so it shows merged work, plus files the running tasks have changed so far."""
from collections import defaultdict
from pathlib import Path

from .. import repomap


def build(run):
    integ = (run.get("integration") or {}).get("path")
    root = Path(integ) if integ and Path(integ).is_dir() else Path(run["repo"])
    if not root.is_dir():
        return {"name": run["repo_name"], "modules": [], "edges": [], "error": "the repo folder is gone"}
    tr = repomap.tree(root)
    split = set(tr["split"])
    touched = defaultdict(lambda: {"nodes": defaultdict(list)})
    for n in run["nodes"]:
        for f in n.get("files") or []:
            touched[repomap.module_of(f, split)]["nodes"][n["id"]].append(f)
    mods = tr["modules"]
    keep = sorted(mods, key=lambda m: (m not in touched, -mods[m]["lines"]))[:repomap.MAX_MODULES]
    keep = set(keep) | set(touched)
    lay = repomap.layers(keep, tr["edges"])
    state = {n["id"]: n["state"] for n in run["nodes"]}
    modules = []
    for m in sorted(keep):
        info = mods.get(m, {"files": 0, "lines": 0, "top": []})
        by_node = touched[m]["nodes"] if m in touched else {}
        modules.append({"id": m, "files": info["files"], "lines": info["lines"], "layer": lay.get(m, 0),
                        "top_files": [f["path"] for f in info["top"][:6]],
                        "tasks": [{"id": nid, "state": state.get(nid), "files": sorted(set(fs))} for nid, fs in sorted(by_node.items())]})
    return {"name": run["repo_name"], "root": str(root), "file_count": tr["file_count"], "modules": modules,
            "edges": [e for e in tr["edges"] if e["from"] in keep and e["to"] in keep]}
