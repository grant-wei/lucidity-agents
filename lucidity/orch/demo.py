"""Demo mode: the bundled toy repo (sample_data/demo/repo) and a scripted run on it.

The plan and each worker round's edits come from sample_data/demo/scenario.json and steps/, so
no key, CLI or network is needed. Everything else is the real loop: each task gets a real git
worktree, the done-when tests really run, the gate really decides, passing work is really merged,
and the budget cap really stops a task. One task fails its check and fixes it on round two; one
runs out of budget and waits for you."""
import json
import shutil
from pathlib import Path

from .. import config
from . import worktrees

DEMO_DIR = config.SAMPLE_DIR / "demo"
REPO_NAME = "tinyshop"


class Scenario:
    def __init__(self, folder=DEMO_DIR):
        self.folder = Path(folder)
        self.data = json.loads((self.folder / "scenario.json").read_text(encoding="utf-8"))

    @property
    def goal(self):
        return self.data["goal"]

    @property
    def budget_usd(self):
        return self.data["budget_usd"]

    @property
    def planner(self):
        return self.data["planner"]

    @property
    def plan(self):
        return self.data["plan"]

    def step(self, node_id, round_no):
        key = f"{node_id}-r{round_no}"
        meta = self.data["steps"].get(key)
        if meta is None:
            return None
        return {**meta, "files_dir": self.folder / "steps" / key}


def prepare_repo(dest):
    """A fresh git repo holding the toy shop, at dest/tinyshop. Returns its path."""
    repo = Path(dest) / REPO_NAME
    if repo.exists():
        shutil.rmtree(repo, ignore_errors=True)
    shutil.copytree(DEMO_DIR / "repo", repo, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc"))
    worktrees.init_repo(repo, "tinyshop: catalog, cart, tax, checkout, api; spec/ holds acceptance tests")
    return repo
