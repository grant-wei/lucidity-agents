"""Bring a CSV: turn any table into a repo Lucidity can run a live goal on.

    python -m lucidity.orch.csvrepo examples/breast_cancer.csv --target diagnosis

The repo gets the table under data/, a deliberately small starting model (two numeric columns), a
scorer under evals/ and a test. Every row's split (train, dev or heldout, about 60/20/20) is written
into data/rows.csv as `_split`, so every run sees the same split. Three ways to split:

  rows    a fixed hash of the row number (the default)
  time    by a date column: oldest 60% train, next 20% dev, newest 20% test, so no model is scored on
          rows older than the ones it learned from (--split-by date_column)
  group   a fixed hash of a column's value, so rows sharing it (one customer, one event) land together
          (--group-by column)

The scorer refuses the test split when an
agent runs it (LUCIDITY_ROLE=agent); only Lucidity, as referee, scores the test rows. evals/ and data/
are protected dirs, so an agent that edits them fails its check unscored.

evals/about.json carries the plain-language split and the reference scores (guessing, the starting
model) that the run page shows next to the numbers.
"""
import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

from .. import config

MAX_BYTES = 50 * 1024 * 1024
MIN_ROWS = 50
MAX_CLASSES = 20
PKG = "tablemodel"


class CsvError(ValueError):
    pass


def _num(v):
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def save_upload(name, data):
    """Keep an uploaded CSV under state/uploads/ and return its path. Same bytes, same file."""
    if not data:
        raise CsvError("that file is empty")
    if len(data) > MAX_BYTES:
        raise CsvError("keep the CSV under 50 MB")
    stem = _slug(Path(name or "table.csv").stem) or "table"
    out = config.STATE_DIR / "uploads" / f"{stem}-{hashlib.sha1(data).hexdigest()[:8]}.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    if not out.exists():
        out.write_bytes(data)
    return str(out)


def read_table(path):
    path = Path(str(path).strip().strip('"')).expanduser()
    if not path.is_absolute() and not path.is_file() and (config.ROOT / path).is_file():
        path = config.ROOT / path   # examples/breast_cancer.csv, whatever folder the server started in
    if not path.is_file():
        raise CsvError(f"no file at {path}")
    if path.stat().st_size > MAX_BYTES:
        raise CsvError("keep the CSV under 50 MB")
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        rows = list(csv.reader(fh))
    rows = [r for r in rows if any(c.strip() for c in r)]
    if len(rows) < MIN_ROWS + 1:
        raise CsvError(f"the CSV needs a header row and at least {MIN_ROWS} data rows")
    header = [h.strip() for h in rows[0]]
    if len(set(header)) != len(header) or not all(header):
        raise CsvError("every column needs a unique, non-empty name in the header row")
    body = [r + [""] * (len(header) - len(r)) for r in rows[1:]]
    return path, header, [dict(zip(header, (c.strip() for c in r))) for r in body]


LAYOUT = b"5"   # bump when the generated repo or about.json changes, so a cached repo isn't reused

DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m", "%Y/%m", "%m/%d/%Y", "%d.%m.%Y", "%Y%m%d", "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%b %Y", "%B %Y", "%d %b %Y")


def _date(v):
    """A sortable date for a cell, or None. A bare 4-digit year counts."""
    v = (v or "").strip()
    if re.fullmatch(r"(18|19|20)\d\d", v):
        return dt.datetime(int(v), 1, 1)
    try:
        return dt.datetime.fromisoformat(v.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        pass
    for f in DATE_FORMATS:
        try:
            return dt.datetime.strptime(v, f)
        except ValueError:
            continue
    return None


def _date_columns(header, rows, target):
    out = []
    for h in header:
        vals = [r[h] for r in rows if r[h] != ""]
        if h != target and len(vals) >= 0.95 * len(rows) and len({*vals}) > 4 and all(_date(v) for v in vals):
            out.append(h)
    return out


def _id_columns(header, rows, target, numeric):
    """Columns that just name the row: a whole number unique to every row, or a name like *_id."""
    out = []
    for h in header:
        if h == target:
            continue
        vals = [r[h] for r in rows if r[h] != ""]
        unique = len(set(vals)) == len(vals) == len(rows)
        if (h in numeric and unique and all(float(v).is_integer() for v in vals)) or \
                (re.search(r"(^|[_ ])id$|^id[_ ]", h, re.I) and len(set(vals)) > len(rows) / 2):
            out.append(h)
    return out


def columns(path):
    """What the composer's column picker needs: every column, and which look like dates or row IDs."""
    path, header, rows = read_table(path)
    numeric = [h for h in header if all(_num(r[h]) is not None for r in rows if r[h] != "") and any(r[h] != "" for r in rows)]
    dates = _date_columns(header, rows, None)
    # Worth grouping by: values that repeat across rows (a customer, a team), not measurements like 12.8.
    groups = [h for h in header if h not in dates and 3 <= len({r[h] for r in rows}) <= len(rows) / 3
              and (h not in numeric or re.search(r"id$|_no$|number$|code$", h, re.I))]
    return {"columns": header, "target": header[-1], "dates": dates, "groups": groups,
            "ids": _id_columns(header, rows, None, numeric), "rows": len(rows)}


def describe(path, target=None):
    """What the CSV holds and what kind of prediction its target column is."""
    path, header, rows = read_table(path)
    target = (target or "").strip() or header[-1]
    if target not in header:
        raise CsvError(f"no column named {target!r}; the columns are {', '.join(header[:30])}")
    rows = [r for r in rows if r[target] != ""]
    if len(rows) < MIN_ROWS:
        raise CsvError(f"only {len(rows)} rows have a value in {target!r}; need at least {MIN_ROWS}")
    values = [r[target] for r in rows]
    counts = Counter(values)
    numeric_target = all(_num(v) is not None for v in values)
    if len(counts) == 2:
        kind = "binary"
    elif len(counts) <= MAX_CLASSES and (not numeric_target or len(counts) <= 10):
        kind = "multiclass"
    elif numeric_target:
        kind = "regression"
    else:
        raise CsvError(f"{target!r} has {len(counts)} different text values; pick a column with at most "
                       f"{MAX_CLASSES} categories, or a number")
    if kind != "regression" and min(counts.values()) < 5:
        raise CsvError(f"some answers in {target!r} appear fewer than 5 times; too few to learn and test on")
    numeric = [h for h in header if h != target and all(_num(r[h]) is not None for r in rows if r[h] != "")
               and any(r[h] != "" for r in rows)]
    return {"path": path, "header": header, "rows": rows, "target": target, "kind": kind,
            "classes": sorted(counts, key=lambda c: (-counts[c], c)) if kind != "regression" else None,
            "numeric": numeric, "dates": _date_columns(header, rows, target),
            "ids": _id_columns(header, rows, target, numeric)}


def split_of_row(row_id):
    b = int(hashlib.sha1(str(row_id).encode()).hexdigest(), 16) % 5
    return "heldout" if b == 0 else "dev" if b == 1 else "train"


def _split_by_time(rows, col):
    """Oldest ~60% train, next ~20% dev, newest ~20% heldout. Rows on the same date stay together."""
    bad = [r[col] for r in rows if not _date(r[col])]
    if bad:
        raise CsvError(f"{len(bad)} rows have no readable date in {col!r} (for example {bad[0]!r}); "
                       "use dates like 2024-03-31")
    when = {r["row_id"]: _date(r[col]) for r in rows}
    days = sorted(set(when.values()))
    count = Counter(when.values())
    cut, seen = {}, 0
    for d in days:
        cut[d] = "train" if seen < 0.6 * len(rows) else "dev" if seen < 0.8 * len(rows) else "heldout"
        seen += count[d]
    for r in rows:
        r["_split"] = cut[when[r["row_id"]]]
    n = Counter(r["_split"] for r in rows)
    if min(n["train"], n["dev"], n["heldout"]) < 10:
        raise CsvError(f"{col!r} has too few different dates to split into train, tune and test by time")
    span = {k: (min(when[r["row_id"]] for r in rows if r["_split"] == k),
                max(when[r["row_id"]] for r in rows if r["_split"] == k)) for k in n}
    yearly = all(d.month == 1 and d.day == 1 for d in days)
    fmt = (lambda d: str(d.year)) if yearly else (lambda d: d.strftime("%Y-%m-%d"))

    def rng(k):
        a, b = span[k]
        return fmt(a) if a == b else f"{fmt(a)} to {fmt(b)}"
    return (f"Rows are split by {col}: trained on {rng('train')} ({n['train']} rows), tuned on {rng('dev')} "
            f"({n['dev']}), tested on {rng('heldout')} ({n['heldout']}), so every model is scored on later rows "
            f"than it learned from. Agents never see the test rows' score; only Lucidity scores them.")


def _split_by_group(rows, col):
    for r in rows:
        r["_split"] = split_of_row("g:" + r[col])
    n = Counter(r["_split"] for r in rows)
    if min(n["train"], n["dev"], n["heldout"]) < 10:
        raise CsvError(f"{col!r} has too few different values to keep each one on one side of the split")
    return (f"Rows are split by {col}, so rows with the same {col} always land together: {n['train']} to "
            f"train, {n['dev']} to tune, {n['heldout']} to test. Agents never see the test rows' score; only "
            f"Lucidity scores them.")


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")[:40] or "table"


# ---------- the files of the generated repo ----------

INIT = '''"""Predicts {target!r} from the other columns of {source}."""
import csv
from pathlib import Path

from .features import NAMES, features
from .model import make_model

DATA = Path(__file__).resolve().parent.parent / "data" / "rows.csv"
TARGET = {target!r}
KIND = {kind!r}            # binary, multiclass or regression
CLASSES = {classes!r}      # for binary, the first is the "yes" whose chance is predicted


def load_rows():
    """Every row as a dict of strings (empty string = missing), plus row_id."""
    with open(DATA, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def label(row):
    """The answer for one row: a class name, or a number for regression."""
    return float(row[TARGET]) if KIND == "regression" else row[TARGET]


def split_of(row):
    """train, dev or heldout, fixed when the table was set up ({split_how}): never reshuffled."""
    return row["_split"]
'''

FEATURES = '''"""What the model sees about a row. Never use {target!r} here: that is the answer.

All columns of data/rows.csv: {columns}.
Numeric columns: {numeric}.
`row_id` and `_split` were added by Lucidity: never use them as inputs.{id_note}
The starting model uses only {names_text}; missing numbers count as 0.
"""
NAMES = {names!r}


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def features(row):
    """One list of numbers, in NAMES order."""
    return {body}
'''

MODEL = '''"""The model: anything scikit-learn-shaped with fit() and {predict}()."""
from sklearn.linear_model import {cls}


def make_model():
    return {cls}({args})
'''

SCORE = '''"""Scores the model on one split. Prints one JSON line.

    python evals/score.py               # train on train + dev rows, score the held-out (test) rows
    python evals/score.py --split dev   # train on train rows, score dev (tune here)

{explain_metric}
When Lucidity runs this for one of its agents (LUCIDITY_ROLE=agent), the held-out split is refused.
With LUCIDITY_EXPLAIN=1 it also reports each input's importance: how much the score worsens when that
input is shuffled across the scored rows.
"""
import argparse
import json
import math
import os
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from {pkg} import CLASSES, KIND, NAMES, features, label, load_rows, make_model, split_of  # noqa: E402

EPS = 1e-6


def probs(model, X):
    """Each row's chance of each class, in CLASSES order, clipped away from 0 and 1."""
    raw = model.predict_proba(X)
    order = [list(model.classes_).index(c) if c in list(model.classes_) else None for c in CLASSES]
    out = []
    for r in raw:
        p = [max(float(r[j]), EPS) if j is not None else EPS for j in order]
        s = sum(p)
        out.append([q / s for q in p])
    return out


def auc(p, y):
    pos = sorted(q for q, t in zip(p, y) if t)
    neg = sorted(q for q, t in zip(p, y) if not t)
    if not pos or not neg:
        return 0.5
    wins, j = 0.0, 0
    for q in pos:   # pairs where a yes outranks a no; ties count half
        while j < len(neg) and neg[j] < q:
            j += 1
        k = j
        while k < len(neg) and neg[k] == q:
            k += 1
        wins += j + (k - j) / 2
    return wins / (len(pos) * len(neg))


def metrics(model, X, y):
    if KIND == "regression":
        pred = [float(v) for v in model.predict(X)]
        mean = sum(y) / len(y)
        sse = sum((a - b) ** 2 for a, b in zip(pred, y))
        sst = sum((b - mean) ** 2 for b in y) or 1.0
        return {{"rmse": round(math.sqrt(sse / len(y)), 4), "r2": round(1 - sse / sst, 4)}}
    P = probs(model, X)
    idx = [CLASSES.index(t) for t in y]
    out = {{"log_loss": round(-sum(math.log(p[i]) for p, i in zip(P, idx)) / len(y), 4),
            "accuracy": round(sum(max(range(len(p)), key=p.__getitem__) == i for p, i in zip(P, idx)) / len(y), 4)}}
    if KIND == "binary":
        out["auc"] = round(auc([p[0] for p in P], [i == 0 for i in idx]), 4)
    return out


HEADLINE = "rmse" if KIND == "regression" else "log_loss"   # lower is better for both


def importance(model, X, y):
    """Rise in the headline score when each input is shuffled, mean of 5 fixed shuffles, biggest first."""
    base = metrics(model, X, y)[HEADLINE]
    out = {{}}
    for j, name in enumerate(NAMES[:len(X[0])]):
        rises = []
        for seed in range(5):
            col = [r[j] for r in X]
            random.Random(seed).shuffle(col)
            rises.append(metrics(model, [list(r[:j]) + [c] + list(r[j + 1:]) for r, c in zip(X, col)], y)[HEADLINE] - base)
        out[name] = round(sum(rises) / len(rises), 4)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", default="heldout", choices=["dev", "heldout"])
    args = ap.parse_args()
    if args.split == "heldout" and os.environ.get("LUCIDITY_ROLE") == "agent":
        # The held-out rows are the referee's test. An agent that could see their score could tune to them.
        print(json.dumps({{"error": "held-out scores are only shown to the referee; tune with --split dev"}}))
        sys.exit(2)
    t0 = time.time()
    rows = load_rows()
    fit_splits = {{"train"}} | ({{"dev"}} if args.split == "heldout" else set())
    fit = [r for r in rows if split_of(r) in fit_splits]
    test = [r for r in rows if split_of(r) == args.split]
    model = make_model()
    model.fit([features(r) for r in fit], [label(r) for r in fit])
    X, y = [features(r) for r in test], [label(r) for r in test]
    out = {{"split": args.split, "rows": len(test), "features": NAMES, "model": type(model).__name__,
            "metrics": metrics(model, X, y), "seconds": round(time.time() - t0, 1)}}
    if os.environ.get("LUCIDITY_EXPLAIN") == "1":
        out["importance"] = importance(model, X, y)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
'''

TEST = '''"""The answer column must never leak into what the model sees."""
from {pkg} import NAMES, TARGET, features, load_rows


def test_one_number_per_name():
    row = load_rows()[0]
    assert len(features(row)) == len(NAMES)
    assert all(isinstance(x, (int, float)) for x in features(row))


def test_answer_is_not_an_input():
    assert TARGET not in NAMES
    row = dict(load_rows()[0])
    before = features(row)
    row[TARGET] = "something else entirely"
    assert features(row) == before, "features() reads the answer column"
'''

README = '''# {name}

Predicts **{target}** ({kind_text}) from the other columns of `{source}`, {n} rows.

- `{pkg}/features.py`: what the model sees (starts with {names_text}).
- `{pkg}/model.py`: the model (starts as plain {cls}).
- `evals/score.py`: the scorer. `python evals/score.py --split dev` to tune; the test split is the referee's.
- `data/rows.csv`: the table, with `row_id` and `_split` columns added. {split}

Rules: don't edit `evals/` or `data/`; keep `python -m pytest -q` passing; never use `{target}` as an input.
Requires scikit-learn.
'''


def _git(repo, *args):
    r = subprocess.run(["git", "-c", "user.name=Lucidity", "-c", "user.email=lucidity@localhost",
                        "-c", "core.autocrlf=false", *args], cwd=repo, capture_output=True, text=True)
    if r.returncode:
        raise CsvError(f"git {args[0]} failed: {(r.stderr or r.stdout).strip()[:300]}")
    return r.stdout


def _score(repo, split):
    r = subprocess.run([sys.executable, "evals/score.py", "--split", split], cwd=repo, capture_output=True,
                       text=True, timeout=300)
    if r.returncode:
        raise CsvError(f"the starting model failed to score: {(r.stderr or r.stdout).strip()[-400:]}")
    return json.loads(r.stdout.strip().splitlines()[-1])["metrics"]


BENCH = """import json, sys
sys.argv = ["score.py", "--split", "heldout"]
sys.path.insert(0, "evals")
import score
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
cols = json.loads(sys.stdin.read())
score.NAMES = cols
def num(v):   # missing counts as 0, as in the starting model
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0
score.features = lambda row: [num(row[c]) for c in cols]
score.make_model = lambda: make_pipeline(StandardScaler(), LinearRegression() if score.KIND == "regression"
                                         else LogisticRegression(penalty=None, max_iter=5000))
score.main()
"""


def _benchmark(repo, cols):
    """Ordinary linear or logistic regression (no penalty) on every usable numeric column, scored on the test
    rows by the repo's own scorer: the textbook model any agent's work should be compared with."""
    if not cols:
        return None
    r = subprocess.run([sys.executable, "-c", BENCH], cwd=repo, input=json.dumps(cols), capture_output=True,
                       text=True, timeout=600, env={**os.environ, "PYTHONWARNINGS": "ignore"})
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])["metrics"]
    except (IndexError, ValueError, KeyError):
        return None   # never block setup on the benchmark


def _guess_score(info, rows):
    """What always guessing the training answer scores on the test rows: the floor any model must beat."""
    train = [r for r in rows if r["_split"] in ("train", "dev")]
    test = [r for r in rows if r["_split"] == "heldout"]
    t = info["target"]
    if info["kind"] == "regression":
        mean = sum(float(r[t]) for r in train) / len(train)
        return math.sqrt(sum((float(r[t]) - mean) ** 2 for r in test) / len(test))
    c = Counter(r[t] for r in train)
    p = {k: max(v / len(train), 1e-6) for k, v in c.items()}
    return -sum(math.log(p.get(r[t], 1e-6)) for r in test) / len(test)


def _fmt(x):
    return f"{x:.4f}" if abs(x) < 1 else f"{x:.2f}" if abs(x) < 100 else f"{x:,.1f}"


MARGIN = 0.998   # the goal beats the best no-agent answer by at least 0.2%, so a tie or a rounding-sized lead doesn't count
COIN_WHY = "Say 50% for every row. Log loss charges 0.693 a row for that, so 0.693 means no skill at all."


def build(csv_path, target=None, out_root=None, split_by=None, group_by=None):
    """Make (or reuse) the repo for this CSV + target. Returns what the composer needs to plan a run.

    split_by: a date column to split by time. group_by: a column whose rows must land together.
    """
    info = describe(csv_path, target)
    src, t, kind = info["path"], info["target"], info["kind"]
    split_by, group_by = (split_by or "").strip() or None, (group_by or "").strip() or None
    if split_by and group_by:
        raise CsvError("split by time or by group, not both")
    for col in (split_by, group_by):
        if col and col not in info["header"]:
            raise CsvError(f"no column named {col!r}")
        if col == t:
            raise CsvError("the column to split by can't be the one being predicted")
    how = f"time:{split_by}" if split_by else f"group:{group_by}" if group_by else "rows"
    digest = hashlib.sha1(src.read_bytes() + b"\0" + t.encode() + b"\0" + how.encode() + b"\0" + LAYOUT).hexdigest()[:8]
    name = f"{_slug(src.stem)}-{digest}"
    repo = Path(out_root or config.STATE_DIR / "csv") / name
    about_path = repo / "evals" / "about.json"
    if about_path.exists() and (repo / ".git").exists() and _git(repo, "rev-list", "-n1", "--all").strip():
        return json.loads(about_path.read_text(encoding="utf-8"))
    if repo.exists():
        import shutil
        shutil.rmtree(repo, ignore_errors=True)

    header, rows = info["header"], info["rows"]
    out_header = ["row_id"] + [h for h in header if h not in ("row_id", "_split")] + ["_split"]
    for i, r in enumerate(rows, 1):
        r["row_id"] = str(i)
        r["_split"] = split_of_row(i)
    split = _split_by_time(rows, split_by) if split_by else _split_by_group(rows, group_by) if group_by else None
    skip = set(info["ids"]) | {split_by, group_by, "row_id", "_split"}
    names = [h for h in info["numeric"] if h not in skip][:2]   # never an ID or the split column
    names_text = (" and ".join(f"`{n}`" for n in names)) if names else "no columns at all (a constant), so it just guesses"
    body = "[" + ", ".join(f"num(row[{n!r}])" for n in names) + "]" if names else "[1.0]   # no numeric column yet: a constant"
    names_list = names or ["constant"]
    cls, args = ("LinearRegression", "") if kind == "regression" else ("LogisticRegression", "max_iter=1000")
    classes = info["classes"]
    if kind == "binary":   # the rarer answer is the "yes" whose chance is predicted
        classes = sorted(classes, key=lambda c: Counter(r[t] for r in rows)[c])
    explain = (f"Lower log loss is better; it also reports AUC and accuracy for predicting {classes[0]!r}." if kind == "binary"
               else "Lower log loss is better; it also reports accuracy." if kind == "multiclass"
               else "Lower RMSE (typical size of the error) is better; it also reports R² (1 is perfect).")
    kind_text = (f"yes/no: {classes[0]} or {classes[1]}" if kind == "binary"
                 else f"one of {len(classes)} classes" if kind == "multiclass" else "a number")

    (repo / PKG).mkdir(parents=True)
    (repo / "data").mkdir()
    (repo / "evals").mkdir()
    (repo / "tests").mkdir()
    with open(repo / "data" / "rows.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=out_header, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    n = Counter(r["_split"] for r in rows)
    split = split or (f"Rows are split by a fixed hash of their row number: {n['train']} to train, {n['dev']} to tune, "
                      f"{n['heldout']} to test. Agents never see the test rows' score; only Lucidity scores them.")
    split_how = f"by {split_by}, oldest first" if split_by else f"by a hash of {group_by}" if group_by else "by a hash of row_id"
    id_note = f"\nThese look like row IDs, not measurements: {', '.join(info['ids'])}." if info["ids"] else ""
    fmt = dict(pkg=PKG, target=t, kind=kind, classes=classes, source=src.name, names=names_list,
               split=split, split_how=split_how, id_note=id_note,
               names_text=names_text, columns=", ".join(out_header), numeric=", ".join(info["numeric"]) or "none",
               body=body, cls=cls, args=args, predict="predict" if kind == "regression" else "predict_proba",
               explain_metric=explain, name=name, n=len(rows),
               kind_text=kind_text)
    (repo / PKG / "__init__.py").write_text(INIT.format(**fmt), encoding="utf-8")
    (repo / PKG / "features.py").write_text(FEATURES.format(**fmt), encoding="utf-8")
    (repo / PKG / "model.py").write_text(MODEL.format(**fmt), encoding="utf-8")
    (repo / "evals" / "score.py").write_text(SCORE.format(**fmt), encoding="utf-8")
    (repo / "tests" / "test_features.py").write_text(TEST.format(**fmt), encoding="utf-8")
    (repo / "tests" / "conftest.py").write_text(
        "import sys\nfrom pathlib import Path\n\nsys.path.insert(0, str(Path(__file__).resolve().parent.parent))\n",
        encoding="utf-8")
    (repo / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
    (repo / "requirements.txt").write_text("scikit-learn>=1.5\n", encoding="utf-8")
    (repo / ".gitignore").write_text("__pycache__/\n.pytest_cache/\n", encoding="utf-8")
    (repo / "README.md").write_text(README.format(**fmt), encoding="utf-8")

    metric = "rmse" if kind == "regression" else "log_loss"
    dev, test = _score(repo, "dev")[metric], _score(repo, "heldout")[metric]
    guess = _guess_score(info, rows)
    usable = [h for h in info["numeric"] if h not in skip]
    bench = _benchmark(repo, usable)
    reg = "linear" if kind == "regression" else "logistic"
    # every answer you could get without agents; the best one is the benchmark, and the goal is to beat it
    references = [{"label": "Always guess the average" if kind == "regression" else "Always guess each answer's share",
                   "value": round(guess, 4), "short": "Guessing",
                   "why": ("Predict the training average for every row." if kind == "regression"
                           else "Say the same thing for every row: how often each answer came up in training.")},
                  {"label": f"The starting model, {len(names)} column{'s' if len(names) != 1 else ''}", "value": round(test, 4),
                   "short": "Starting model", "why": f"Plain {reg} regression on just {', '.join(names) or 'no columns'}."}]
    if kind == "binary":
        references.insert(0, {"label": "Coin flip (always 50%)", "value": 0.6931, "short": "Coin flip", "why": COIN_WHY})
    bench_label = f"Plain {reg} regression on all {len(usable)} columns"
    if bench and isinstance(bench.get(metric), (int, float)):
        references.append({"label": bench_label, "value": bench[metric], "short": "Plain regression",
                           "why": f"Ordinary {reg} regression on every number column, no tuning. The five-minute model."})
    best = min(references, key=lambda r: r["value"])
    best["benchmark"] = True
    goal_value = round(best["value"] * MARGIN, 4)
    plain = (f"whether {t} is {classes[0]!r}" if kind == "binary"
             else f"{t} (one of {len(classes)} classes)" if kind == "multiclass" else t)
    keep = "without accuracy dropping" if kind != "regression" else "without R² dropping"
    goal = (f"Get held-out {metric.replace('_', ' ')} to {_fmt(goal_value)} or lower ({best['label'][0].lower() + best['label'][1:]} "
            f"scores {_fmt(best['value'])}; the repo scores {_fmt(test)}) "
            f"for predicting {plain} from {src.name}, {keep}. Tune on the dev split; the tests must keep passing. "
            f"The starting model uses only {len(names)} of {len(info['numeric'])} numeric columns. Ask the owner which "
            f"model families to try (for example regularized {'linear' if kind == 'regression' else 'logistic'} "
            f"regression on all columns, random forest, boosted trees), then build each one in parallel and keep the best.")
    about = {"repo": str(repo), "eval_command": "python evals/score.py", "goal": goal, "budget_usd": 1.0,
             "title": f"{src.stem} · predict {t}", "kind": kind, "metric": metric, "target": t, "rows": len(rows),
             "columns": len(header), "numeric_columns": len(info["numeric"]), "start_dev": dev, "start_test": test,
             "blurb": (f"A model predicts {plain} from the other columns of {src.name} ({len(rows):,} rows). "
                       f"The starting model scores {_fmt(test)} {metric.replace('_', ' ')} on the test rows. The best "
                       f"answer without agents is {best['label'][0].lower() + best['label'][1:]} at {_fmt(best['value'])}, "
                       f"so the goal is {_fmt(goal_value)}."),
             "split": split, "split_how": how, "references": references,
             # how the goal was set, shown next to it in the composer
             "goal_value": goal_value, "goal_rule": "beat the best answer without agents by at least 0.2%",
             "lower_is_better": True, "start_columns": names, "start_model": cls,
             "benchmark": best,
             "regression": ({"label": bench_label, "value": bench[metric], "model": cls, "columns": len(usable),
                             "penalty": "none"} if bench and isinstance(bench.get(metric), (int, float)) else None)}
    about_path.write_text(json.dumps(about, indent=1), encoding="utf-8")
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", f"{PKG}: predict {t} from {src.name}, starting model on {len(names)} columns, evals/score.py")
    return about


def main():
    ap = argparse.ArgumentParser(description="Turn a CSV into a repo Lucidity can run a live goal on.")
    ap.add_argument("csv")
    ap.add_argument("--target", help="the column to predict (default: the last column)")
    ap.add_argument("--split-by", help="a date column: train on the oldest rows, test on the newest")
    ap.add_argument("--group-by", help="a column whose rows must stay on one side of the split")
    ap.add_argument("--out", help="where to put the repo (default: state/csv/)")
    a = ap.parse_args()
    try:
        about = build(a.csv, a.target, a.out, a.split_by, a.group_by)
    except CsvError as e:
        sys.exit(f"error: {e}")
    print(json.dumps(about, indent=1))


if __name__ == "__main__":
    main()
