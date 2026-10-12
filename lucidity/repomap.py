"""The architecture map, in plain code: for every repo the agents edited, split it into modules,
draw the import links between them, and attribute each session's edits (and, approximately,
its cost) to the modules it touched. No model here; the architect agent only adds a one-line
role per module on top of this."""
import hashlib
import os
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

from . import config
from .readers import age_minutes, git_root
from .touches import import_lines

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "env", "__pycache__", "dist", "build", ".next", ".pytest_cache",
             ".mypy_cache", ".ruff_cache", "target", ".idea", ".vscode", "coverage", ".turbo", "out", "logs", "state"}
CODE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".go", ".rs", ".java", ".rb", ".php", ".cs",
            ".swift", ".kt", ".c", ".h", ".cpp", ".css", ".scss", ".html", ".sql", ".sh", ".ps1"}
DOC_EXT = {".md", ".json", ".yaml", ".yml", ".toml"}
SPLIT_DIRS = {"src", "lib", "app", "apps", "packages", "pkg", "internal", "services", "server", "backend", "frontend"}
# never opened deeper: generated output, data and history are one box each, however big
NOT_SOURCE = {"data", "output", "outputs", "archive", "docs", "notes", "tmp", "reports", "artifacts", "fixtures",
              "examples", "memory", "public", "static", "assets", "vendor", "third_party", "migrations"}
SOURCE_EXT = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".go", ".rs", ".java", ".rb", ".php", ".cs", ".swift", ".kt",
              ".c", ".cpp"}
MAX_FILES = 6000
MAX_MODULES = 18
_SAMPLE_PREFIX = re.compile(r"^/(?:Users/sam/code|home/priya/projects)/([^/]+)/(.+)$")

_tree_cache = {}   # root -> (signature, tree)


# ---------- where a touched file lives ----------

def locate(path, mode):
    """(repo root, path relative to it) for a touched file, or (None, None) if it isn't in a repo.
    Sample sessions use invented paths; they map onto the fixture repos in sample_data/fixtures."""
    p = str(path).replace("\\", "/")
    if mode != "local":
        m = _SAMPLE_PREFIX.match(p)
        root = config.SAMPLE_DIR / "fixtures" / m.group(1) if m else None
        return (root, m.group(2)) if root and root.is_dir() else (None, None)
    root = git_root(p)
    if not root:
        return None, None
    try:
        return root, Path(p).resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        try:
            return root, Path(p).relative_to(root).as_posix()
        except ValueError:
            return None, None


# ---------- the repo itself ----------

def _keep(rel):
    parts = rel.split("/")
    if any(d in SKIP_DIRS or d.startswith(".") for d in parts[:-1]):
        return False
    ext = os.path.splitext(parts[-1])[1].lower()
    return ext in CODE_EXT or ext in DOC_EXT


def _is_code(rel):
    return os.path.splitext(rel)[1].lower() in CODE_EXT


def _walk(root):
    """The repo's files: what git tracks when it can say (fast, and skips ignored data folders),
    else a walk of the folder. Code files come first, so a repo full of data still shows its shape."""
    files = None
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "-z"], capture_output=True, timeout=15)
        if r.returncode == 0 and r.stdout:
            files = [f for f in r.stdout.decode("utf-8", "replace").split("\0") if f and _keep(f)]
    except (OSError, subprocess.SubprocessError):
        pass
    if files is None:
        files = []
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS and not d.startswith("."))
            files += [Path(dirpath, f).relative_to(root).as_posix() for f in filenames]
            if len(files) >= MAX_FILES * 5:
                break
        files = [f for f in files if _keep(f)]
    ordered = [f for f in files if _is_code(f)] + [f for f in files if not _is_code(f)]
    return sorted(ordered[:MAX_FILES]), len(files)


def _read(root, rel, limit=400_000):
    try:
        p = Path(root) / rel
        if p.stat().st_size > limit:
            return ""
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def module_of(rel, split):
    """Which module a file belongs to: the folder one level below the deepest split folder above it
    (or its top folder). Files sitting directly in a split folder belong to that folder."""
    parts = rel.split("/")
    if len(parts) == 1:
        return "(root)"
    depth = 0
    for i in range(1, len(parts)):
        if "/".join(parts[:i]) in split:
            depth = i
    if depth and len(parts) == depth + 1:
        return "/".join(parts[:depth])
    return "/".join(parts[:depth + 1])


def _split_dirs(info):
    """Folders to open one level deeper: the usual source folders, plus any module that holds over
    40% of the code and has subfolders (a single-package repo like src/<name>/...), up to 3 deep."""
    code = {f: i["lines"] for f, i in info.items()
            if "/" in f and os.path.splitext(f)[1].lower() in SOURCE_EXT
            and not any(d.lower() in NOT_SOURCE for d in f.split("/")[:-1])}
    total = sum(code.values()) or 1
    split = {f.split("/")[0] for f in code if f.split("/")[0] in SPLIT_DIRS and f.count("/") >= 2}
    for _ in range(3):
        sizes = Counter()
        for f, n in code.items():
            sizes[module_of(f, split)] += n
        grew = False
        for mod, n in sizes.items():
            subs = {f[len(mod) + 1:].split("/")[0] for f in code if f.startswith(mod + "/") and f.count("/") > mod.count("/") + 1}
            parent = mod.rsplit("/", 1)[0] if "/" in mod else None
            only_child = parent in split and sum(1 for m in sizes if m.startswith(parent + "/")) == 1
            if mod != "(root)" and mod not in split and len(subs) >= 2 and (n / total > 0.4 or only_child):
                split.add(mod)
                grew = True
        if not grew:
            break
    return split


_file_cache = {}   # (path, mtime, size) -> facts; repo files are only re-read when they change


def _facts(root, rel):
    p = Path(root) / rel
    try:
        st = p.stat()
    except OSError:
        return {"code": False, "lines": 0, "doc": "", "imports": []}
    key = (str(p), st.st_mtime_ns, st.st_size)
    hit = _file_cache.get(key)
    if hit:
        return hit
    code = _is_code(rel)
    text = _read(root, rel) if code else ""   # docs and data count as files, not lines
    parse = os.path.splitext(rel)[1] in (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs")
    out = {"code": code, "lines": text.count("\n") if text else (st.st_size // 40 if code else 0),
           "doc": _doc_line(text), "imports": import_lines(text) if parse else []}
    _file_cache[key] = out
    return out


def _doc_line(text):
    """The first docstring or comment line of a file: what its author said it is for."""
    m = re.search(r'^\s*(?:"""|\'\'\')\s*(.+?)\s*$', text[:2000], re.M)
    if m:
        return m.group(1).strip('"\' ')[:160]
    m = re.search(r"^\s*(?://|#|/\*\*?)\s*(\w.+?)\s*(?:\*/)?$", text[:1200], re.M)
    return m.group(1)[:160] if m else ""


def _resolver(files):
    """Map an import string, seen in a given file, to a file in the repo (or None)."""
    by_dotted = {}
    exts = (".py", ".ts", ".tsx", ".js", ".jsx", ".mjs")
    fileset = set(files)
    for f in files:
        if not f.endswith(".py"):
            continue
        parts = f[:-3].split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        for i in range(len(parts)):  # src/payments/refunds -> payments.refunds too
            by_dotted.setdefault(".".join(parts[i:]), f)

    def resolve(name, src):
        if not name:
            return None
        if src.endswith(".py"):
            if name.startswith("."):
                dots = len(name) - len(name.lstrip("."))
                base = src.split("/")[:-1]
                base = base[:len(base) - (dots - 1)] if dots > 1 else base
                name = ".".join(base + [name.lstrip(".")]) if name.lstrip(".") else ".".join(base)
            parts = name.split(".")
            for i in range(len(parts), 0, -1):
                hit = by_dotted.get(".".join(parts[:i]))
                if hit:
                    return hit
            return None
        if name.startswith("."):
            base = Path(src).parent
            cand = os.path.normpath(str(base / name)).replace("\\", "/")
        elif name.startswith("@/") or name.startswith("~/"):
            cand = "src/" + name[2:]
        else:
            return None
        for c in [cand] + [cand + e for e in exts] + [cand + "/index" + e for e in exts]:
            if c in fileset:
                return c
        return None
    return resolve


def tree(root):
    """Modules, files, line counts and import edges of one repo. Cached until its file list changes."""
    files, total = _walk(root)
    sig = hashlib.sha1("\n".join(files).encode()).hexdigest()[:16]
    hit = _tree_cache.get(str(root))
    if hit and hit[0] == sig:
        return hit[1]
    info = {f: _facts(root, f) for f in files}
    split = _split_dirs(info)
    resolve = _resolver(files)
    modules = defaultdict(lambda: {"files": 0, "lines": 0, "top": []})
    edges = Counter()
    for f, i in info.items():
        mod = module_of(f, split)
        m = modules[mod]
        m["files"] += 1
        m["lines"] += i["lines"]
        m["top"].append({"path": f, "lines": i["lines"], "doc": i["doc"]})
        for target in {resolve(imp, f) for imp in i["imports"]}:
            if target and target != f:
                tm = module_of(target, split)
                if tm != mod:
                    edges[(mod, tm)] += 1
    for m in modules.values():
        m["top"].sort(key=lambda x: -x["lines"])
    out = {"sig": sig, "split": sorted(split), "modules": dict(modules),
           "edges": [{"from": a, "to": b, "count": n} for (a, b), n in sorted(edges.items())],
           "file_count": total, "truncated": total > len(files)}
    _tree_cache[str(root)] = (sig, out)
    return out


def layers(module_ids, edges):
    """Row for each module: things that import others sit above the things they import.
    Height = longest import chain below a module; cycles are cut where they close."""
    below = defaultdict(set)
    for e in edges:
        if e["from"] in module_ids and e["to"] in module_ids:
            below[e["from"]].add(e["to"])
    memo = {}

    def height(m, seen=()):
        if m in memo:
            return memo[m]
        if m in seen:
            return 0
        h = max((height(x, seen + (m,)) + 1 for x in below[m]), default=0)
        memo[m] = h
        return h
    return {m: height(m) for m in module_ids}


# ---------- attributing sessions to modules ----------

def build(sessions, mode, now):
    """The whole map: one entry per repo any session edited."""
    per_repo = defaultdict(list)
    outside = 0
    for s in sessions:
        for t in s.touches:
            root, rel = locate(t["path"], mode)
            if not root:
                outside += 1
                continue
            per_repo[root].append((s, t, rel))
    repos = []
    for root, rows in per_repo.items():
        repos.append(_repo_entry(root, rows, now))
    repos.sort(key=lambda r: (-r["edits"], r["name"]))
    return {"repos": repos, "edits_outside_repos": outside}


def _repo_entry(root, rows, now):
    tr = tree(root)
    split = set(tr["split"])
    by_session = defaultdict(list)
    for s, t, rel in rows:
        by_session[s.id].append((s, t, rel))
    touches, sessions = [], []
    touched_mods = Counter()
    for sid, items in by_session.items():
        s = items[0][0]
        weight = sum(t["added"] + t["removed"] for _, t, _ in items) or 1
        mods = Counter()
        for _, t, rel in items:
            mod = module_of(rel, split)
            size = t["added"] + t["removed"]
            # a session's cost, split across the files it edited by lines changed: an approximation
            usd = s.usd * (size or 1) / weight if weight else 0
            touches.append({"session": sid, "module": mod, "file": rel, "t": t["t"], "op": t["op"],
                            "added": t["added"], "removed": t["removed"], "usd": round(usd, 4),
                            "imports_added": t.get("imports_added", [])[:6], "event": t.get("event")})
            mods[mod] += 1
            touched_mods[mod] += 1
        last = max((t["t"] or "" for _, t, _ in items), default="")
        sessions.append({"id": sid, "tool": s.tool, "model": s.model, "project": s.project,
                         "first_prompt": (s.first_prompt or "")[:200], "usd": s.usd,
                         "first_edit": min((t["t"] or "" for _, t, _ in items), default=""), "last_edit": last,
                         "idle_min": round(age_minutes(s.last_activity, now) or 0, 1),
                         "modules": dict(mods)})
    sessions.sort(key=lambda x: x["last_edit"], reverse=True)
    mods = tr["modules"]
    keep = sorted(mods, key=lambda m: (m not in touched_mods, -mods[m]["lines"]))[:MAX_MODULES]
    keep = set(keep) | set(touched_mods)
    hidden = [m for m in mods if m not in keep]
    lay = layers(keep, tr["edges"])
    modules = [{"id": m, "files": mods[m]["files"], "lines": mods[m]["lines"], "layer": lay.get(m, 0),
                "top_files": mods[m]["top"][:8]} for m in sorted(keep) if m in mods]
    # a touched file that no longer exists (deleted, or outside the walk) still gets a box
    for m in touched_mods:
        if m not in mods:
            modules.append({"id": m, "files": 0, "lines": 0, "layer": 0, "top_files": [], "gone": True})
    return {"name": root.name, "sig": tr["sig"], "file_count": tr["file_count"], "truncated": tr["truncated"],
            "modules": modules, "hidden_modules": len(hidden),
            "edges": [e for e in tr["edges"] if e["from"] in keep and e["to"] in keep],
            "sessions": sessions, "touches": touches, "edits": len(touches)}
