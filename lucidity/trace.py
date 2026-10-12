"""A record of one refresh: which steps ran, which tools they called, and what each cost.
The flow view in the UI and the report's traced run both draw from this."""
import json
import time
import uuid
from datetime import datetime, timezone

from . import config
from .redact import redact

TRACE_DIR = config.LOG_DIR / "traces"


class Trace:
    def __init__(self, mode):
        self.id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:4]
        self.mode = mode
        self.nodes = []
        self.edges = []
        self.started = time.time()

    def node(self, node_id, label, kind, parent=None, **info):
        n = {"id": node_id, "label": label, "kind": kind, "tools": [], "tokens": 0, "usd": 0.0,
             "input": "", "output": "", "note": ""}
        n.update(info)
        self.nodes.append(n)
        if parent:
            self.edges.append([parent, node_id])
        return n

    def get(self, node_id):
        return next((n for n in self.nodes if n["id"] == node_id), None)

    def tool(self, node_id, name, args, result):
        n = self.get(node_id)
        if n is not None:
            n["tools"].append({"name": name, "args": redact(json.dumps(args))[:300],
                               "result": redact(str(result))[:800]})

    def charge(self, node_id, row):
        n = self.get(node_id)
        if n is not None and row:
            n["tokens"] += (row.get("input_tokens") or 0) + (row.get("output_tokens") or 0)
            n["usd"] = round(n["usd"] + (row.get("usd") or 0), 6)
            n.setdefault("usage", []).append(row)

    def to_dict(self):
        return {"id": self.id, "mode": self.mode, "nodes": self.nodes, "edges": self.edges,
                "seconds": round(time.time() - self.started, 2),
                "tokens": sum(n["tokens"] for n in self.nodes),
                "usd": round(sum(n["usd"] for n in self.nodes), 6)}

    def save(self):
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        (TRACE_DIR / f"{self.id}.json").write_text(json.dumps(self.to_dict(), indent=1), encoding="utf-8")
