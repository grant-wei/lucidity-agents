"""File edits pulled out of agent tool calls: which file, how many lines in and out, and any
import lines the edit added. Plain code; the architecture map is built from these."""
import re

_PATCH_FILE = re.compile(r"^\*\*\* (Add|Update|Delete) File: (.+?)\s*$", re.M)
_PY_IMPORT = re.compile(r"^\s*(?:from\s+([.\w]+)\s+import\b|import\s+([\w.]+))", re.M)
_JS_IMPORT = re.compile(r"""(?:^\s*import\s[^'"\n]*?from\s*|^\s*import\s*|require\(\s*)['"]([^'"]+)['"]""", re.M)

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def _lines(text):
    return len(text.splitlines()) if text else 0


def import_lines(text):
    """Module names imported by a piece of code (Python or JS/TS)."""
    out = [a or b for a, b in _PY_IMPORT.findall(text or "")]
    out += _JS_IMPORT.findall(text or "")
    return out


def from_claude(name, inp):
    """Touches for one Claude Code tool call, or [] if it doesn't edit a file."""
    if name not in EDIT_TOOLS or not isinstance(inp, dict):
        return []
    path = inp.get("file_path") or inp.get("notebook_path")
    if not path:
        return []
    if name == "Write":
        new, old = inp.get("content") or "", ""
    elif name == "MultiEdit":
        edits = inp.get("edits") or []
        new = "\n".join(e.get("new_string") or "" for e in edits if isinstance(e, dict))
        old = "\n".join(e.get("old_string") or "" for e in edits if isinstance(e, dict))
    elif name == "NotebookEdit":
        new, old = inp.get("new_source") or "", ""
    else:
        new, old = inp.get("new_string") or "", inp.get("old_string") or ""
    added = set(import_lines(new)) - set(import_lines(old))
    return [{"path": path, "op": "write" if name == "Write" else "edit",
             "added": _lines(new), "removed": _lines(old), "imports_added": sorted(added)}]


def from_patch_text(text):
    """Touches in apply_patch text. Codex sometimes wraps the patch in a JS string inside an
    `exec` call, so escaped newlines are unescaped first."""
    if not text or "*** Begin Patch" not in text:
        return []
    if "\n" not in text or ("\\n*** " in text and text.count("\\n") > text.count("\n")):
        text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace('\\"', '"').replace("\\'", "'")
    heads = list(_PATCH_FILE.finditer(text))
    out = []
    for i, m in enumerate(heads):
        end = heads[i + 1].start() if i + 1 < len(heads) else len(text)
        body = text[m.end():end].split("*** End Patch")[0]
        plus = [ln[1:] for ln in body.splitlines() if ln.startswith("+")]
        minus = [ln[1:] for ln in body.splitlines() if ln.startswith("-")]
        op = {"Add": "write", "Update": "edit", "Delete": "delete"}[m.group(1)]
        added = set(import_lines("\n".join(plus))) - set(import_lines("\n".join(minus)))
        out.append({"path": m.group(2).strip().strip('"'), "op": op, "added": len(plus), "removed": len(minus),
                    "imports_added": sorted(added)})
    return out
