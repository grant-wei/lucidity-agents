"""Demo mode: bundled toy repos (sample_data/demos/<name>/repo) and a scripted run on each.

The plan and each worker round's edits come from the demo's scenario.json and steps/, so no key,
CLI or network is needed. Everything else is the real loop: each task gets a real git worktree,
the done-when tests and evals really run, the gate really decides, passing work is really merged,
and the budget cap really stops a task.

  complaints  an LLM router for real CFPB consumer complaints; contracts are held-out accuracy and
            "no product's F1 drops more than 0.05". Replayed from a live run; one agent reports 0.85
            when the eval measures 0.847. The model's answers ship with the demo, so no key is needed.
  invoices  an invoice field extractor; contracts are eval scores (F1 per field on a held-out
            set) and "no field gets worse". One agent claims success while breaking another field.
  shop      a toy shop gets discount codes; contracts are unit and acceptance tests."""
import json
import shutil
from pathlib import Path

from .. import config
from . import worktrees

DEMOS_DIR = config.SAMPLE_DIR / "demos"
DEFAULT = "complaints"


def names():
    return sorted(p.name for p in DEMOS_DIR.iterdir() if (p / "scenario.json").is_file()) if DEMOS_DIR.is_dir() else []


class Scenario:
    def __init__(self, name=DEFAULT):
        if name not in names():
            raise ValueError(f"no demo called {name!r}")
        self.name = name
        self.folder = DEMOS_DIR / name
        self.data = json.loads((self.folder / "scenario.json").read_text(encoding="utf-8"))

    def __getattr__(self, key):
        if key in ("goal", "budget_usd", "planner", "plan", "repo_name", "title", "blurb"):
            return self.data[key]
        raise AttributeError(key)

    def card(self):
        """What the composer shows for this demo."""
        return {"name": self.name, "title": self.title, "blurb": self.blurb, "goal": self.goal,
                "budget_usd": self.budget_usd, "repo_name": self.repo_name, "about_repo": self.data["about_repo"]}

    def step(self, node_id, round_no):
        key = f"{node_id}-r{round_no}"
        meta = self.data["steps"].get(key)
        if meta is None:
            return None
        return {**meta, "files_dir": self.folder / "steps" / key}


def cards():
    out = [Scenario(n).card() for n in names()]
    out.sort(key=lambda c: c["name"] != DEFAULT)
    return out


def prepare_repo(dest, scenario):
    """A fresh git repo holding the demo's toy project, at dest/<repo_name>. Returns its path."""
    repo = Path(dest) / scenario.repo_name
    if repo.exists():
        shutil.rmtree(repo, ignore_errors=True)
    shutil.copytree(scenario.folder / "repo", repo,
                    ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
    worktrees.init_repo(repo, scenario.data["commit_message"])
    seed = scenario.data.get("seed_cache")
    if seed:   # recorded model answers, written where the demo repo's own cache looks (its git dir)
        into = repo / ".git" / seed["into"]
        into.mkdir(parents=True, exist_ok=True)
        answers = json.loads((scenario.folder / seed["file"]).read_text(encoding="utf-8"))
        for key, answer in answers.items():
            (into / f"{key}.json").write_text(json.dumps({"model": "gpt-6-luna", "answer": answer}), encoding="utf-8")
    return repo
