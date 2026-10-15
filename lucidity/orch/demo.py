"""Demo mode: bundled toy repos (sample_data/demos/<name>/repo) and a scripted run on each.

The plan and each worker round's edits come from the demo's scenario.json and steps/, so no key,
CLI or network is needed. Everything else is the real loop: each task gets a real git worktree,
the done-when tests and evals really run, the gate really decides, passing work is really merged,
and the budget cap really stops a task.

  nba       NBA home-win probabilities from 15 seasons of real results; the contract is held-out log
            loss <= 0.610 with no accuracy drop. Replayed from a live run: the planner asks which model
            families to try, the person picks, and one agent per pick builds it. The SVM wins at 0.6052,
            beating FiveThirtyEight's 0.608.
  fed       will the Fed raise rates next month, from FRED Treasury yields, unemployment and CPI
            (1985-2026, held out from 2015); the contract is held-out log loss <= 0.340 (the repo scores
            0.462, the base rate 0.421). Replayed from a live run: random forest wins at 0.2723, kNN
            also passes, and the 3-month yield's gap over the Fed's rate is its biggest predictor.
  stocks    which of 49 industries beats the median next month, from monthly returns 1970-2026; the
            contract is held-out log loss <= 0.6925 (a coin flip scores 0.6931). Replayed from a live run:
            six model families race, none clears the bar, and nothing merges. The honest answer.
  credit    which of 30,000 credit-card customers miss next month's payment (UCI), without sex, age or
            marital status; the contract is held-out log loss <= 0.440 (the repo scores 0.472). Replayed
            from a live run: six families race, random forest wins at 0.4227, kNN and SVM miss.
  complaints  (runnable by name, not in the picker) an LLM router for real CFPB consumer complaints; contracts are held-out accuracy and
            "no product's F1 drops more than 0.05". Replayed from a live run: two prompt strategies,
            two agents each, race in parallel with a parser task; one of five agents passes and merges.
            The model's answers ship with the demo, so no key is needed.
  invoices  an invoice field extractor; contracts are eval scores (F1 per field on a held-out
            set) and "no field gets worse". One agent claims success while breaking another field.
  shop      a toy shop gets discount codes; contracts are unit and acceptance tests."""
import json
import shutil
from pathlib import Path

from .. import config
from . import contracts, worktrees

DEMOS_DIR = config.SAMPLE_DIR / "demos"
DEFAULT = "nba"
SHOWN = {"nba": "Six models race to beat FiveThirtyEight",       # the composer's picker, in this order
         "fed": "Six models call the Fed's next hike",
         "credit": "Six models predict who misses a payment",
         "stocks": "Six models try to beat a coin flip on stocks"}


def names():
    return sorted(p.name for p in DEMOS_DIR.iterdir() if (p / "scenario.json").is_file()) if DEMOS_DIR.is_dir() else []


class Scenario:
    def __init__(self, name=DEFAULT):
        if name not in names():
            raise ValueError(f"no demo called {name!r}")
        self.name = name
        self.folder = DEMOS_DIR / name
        self.data = json.loads((self.folder / "scenario.json").read_text(encoding="utf-8"))
        contracts.load_known_scores(self.folder)

    def __getattr__(self, key):
        if key in ("goal", "budget_usd", "planner", "plan", "repo_name", "title", "blurb"):
            return self.data[key]
        raise AttributeError(key)

    def card(self):
        """What the composer shows for this demo."""
        return {"name": self.name, "title": self.title, "blurb": self.blurb, "goal": self.goal,
                "budget_usd": self.budget_usd, "repo_name": self.repo_name, "about_repo": self.data["about_repo"],
                "split": self.data.get("split"), "references": self.data.get("references", [])}

    def step(self, node_id, round_no):
        key = f"{node_id}-r{round_no}"
        meta = self.data["steps"].get(key)
        if meta is None:
            return None
        return {**meta, "files_dir": self.folder / "steps" / key}


def cards():
    """The demos the composer offers. The others still run by name."""
    have = set(names())
    return [{**Scenario(n).card(), "short": s} for n, s in SHOWN.items() if n in have]


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
