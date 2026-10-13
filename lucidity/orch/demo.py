"""Demo mode: bundled toy repos (sample_data/demos/<name>/repo) and a scripted run on each.

The plan and each worker round's edits come from the demo's scenario.json and steps/, so no key,
CLI or network is needed. Everything else is the real loop: each task gets a real git worktree,
the done-when tests and evals really run, the gate really decides, passing work is really merged,
and the budget cap really stops a task.

  invoices  an invoice field extractor; contracts are eval scores (F1 per field on a held-out
            set) and "no field gets worse". One agent claims success while breaking another field.
  shop      a toy shop gets discount codes; contracts are unit and acceptance tests."""
import json
import shutil
from pathlib import Path

from .. import config
from . import worktrees

DEMOS_DIR = config.SAMPLE_DIR / "demos"
DEFAULT = "invoices"


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
    return repo
