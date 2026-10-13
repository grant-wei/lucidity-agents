"""A run: one goal, planned into tasks, worked by agents, gated by checks, merged when they pass.

    planning -> plan_ready -> running -> done
                                  \\-> needs_you  (a check failed every round, a budget hit its cap,
                                  |                a merge conflicted, or a rubric needs a person)
                                  \\-> stopped

Every task (node) lives in its own git worktree off the run's integration branch. A task is done
only when the gate passes it AND its branch merges cleanly; the run is done when every task is.
State is kept in memory, written to state/runs/<id>.json on every change, and is what the page draws."""
import json
import re
import shutil
import threading
import time
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .. import config
from ..agents import planner as planner_agent
from ..guard import BudgetExceeded
from ..llm import ModelCallFailed
from . import contracts, demo, gate, worktrees
from .workers import LIVE, DemoWorker

ACTIVE = ("queued", "running")
FINISHED = ("done", "skipped")
TICK_S = 0.25
SAMPLE_S = 1.0
MAX_EVENTS = 600

_registry = {}
_registry_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def runs_dir():
    return config.STATE_DIR / "runs"


def work_dir():
    return config.STATE_DIR / "worktrees"


class RunError(ValueError):
    """A request the run can't accept (bad repo, budget over the cap, unknown action...)."""


class Run:
    def __init__(self, data, worker=None):
        self.d = data
        self.lock = threading.RLock()
        self.merge_lock = threading.Lock()
        self.cancel = threading.Event()
        self.worker = worker
        self.thread = None
        self._t0 = time.time() - (data.get("elapsed_s") or 0)
        self._last_sample = 0.0
        self._last_save = 0.0
        self.dir, self.wdir = runs_dir(), work_dir()   # fixed at creation, so a run never writes somewhere else

    # ---------- bookkeeping ----------

    @property
    def id(self):
        return self.d["id"]

    def node(self, nid):
        for n in self.d["nodes"]:
            if n["id"] == nid:
                return n
        raise RunError(f"no task {nid}")

    def elapsed(self):
        return round(time.time() - self._t0, 2)

    def event(self, kind, text, node=None, level="info"):
        with self.lock:
            self.d["events"].append({"s": self.elapsed(), "t": _now(), "kind": kind, "node": node,
                                     "text": text[:600], "level": level})
            del self.d["events"][:-MAX_EVENTS]
        self.save()

    def spend(self, usd, node=None, what="worker"):
        with self.lock:
            self.d["spent_usd"] = round(self.d["spent_usd"] + usd, 6)
            if node is not None:
                node["spent_usd"] = round(node["spent_usd"] + usd, 6)
            self.d["spend_by"][what] = round(self.d["spend_by"].get(what, 0) + usd, 6)
        self.sample(force=True)

    def sample(self, force=False):
        with self.lock:
            now = time.time()
            if not force and now - self._last_sample < SAMPLE_S:
                return
            self._last_sample = now
            states = [n["state"] for n in self.d["nodes"]]
            self.d["samples"].append({
                "s": self.elapsed(), "done": sum(s == "done" for s in states), "running": states.count("running"),
                "queued": states.count("queued"), "needs_you": states.count("needs_you"),
                "skipped": states.count("skipped"), "usd": self.d["spent_usd"]})
            if len(self.d["samples"]) > 2000:   # keep long runs light: thin the oldest half
                self.d["samples"] = self.d["samples"][:1000:2] + self.d["samples"][1000:]

    def save(self, force=True):
        with self.lock:
            if not force and time.time() - self._last_save < 1:
                return
            self._last_save = time.time()
            self.d["elapsed_s"] = self.elapsed()
            self.d["updated"] = _now()
            self.dir.mkdir(parents=True, exist_ok=True)
            tmp = self.dir / f"{self.id}.json.tmp"
            tmp.write_text(json.dumps(self.d, default=str), encoding="utf-8")
            tmp.replace(self.dir / f"{self.id}.json")

    def set_state(self, state, reason=""):
        with self.lock:
            changed = self.d["state"] != state
            self.d["state"], self.d["reason"] = state, reason
            if state in ("done", "stopped", "failed") and not self.d.get("finished"):
                self.d["finished"] = _now()
        if changed:
            self.sample(force=True)
            self.save()

    def view(self):
        with self.lock:
            out = json.loads(json.dumps(self.d, default=str))
        out["elapsed_s"] = self.elapsed() if out["state"] in ("planning", "running") else out.get("elapsed_s", 0)
        out["needs"] = [{"node": n["id"], "title": n["title"], "reason": n["reason"], "kind": n.get("needs_kind"),
                         "actions": _actions_for(n)} for n in out["nodes"] if n["state"] == "needs_you"]
        if out["state"] == "needs_you" and out.get("needs_kind") == "run_budget":
            out["needs"].insert(0, {"node": None, "title": "Run budget", "reason": out["reason"], "kind": "run_budget",
                                    "actions": ["raise_budget", "stop"]})
        return out

    # ---------- planning ----------

    def plan_async(self):
        threading.Thread(target=self._plan, daemon=True, name=f"plan-{self.id}").start()

    def _plan(self):
        try:
            if self.d["mode"] == "demo":
                sc = self.worker.scenario
                pause = sc.planner["seconds"] * self.worker.speed / max(1, len(sc.planner["activity"]))
                for line in sc.planner["activity"]:
                    self.event("planner", line)
                    time.sleep(pause)
                clean, problems = planner_agent.validate_plan(planner_agent.Plan.model_validate(sc.plan), self.d["budget_usd"])
                self.spend(sc.planner["usd"], what="planner")
            else:
                self.event("planner", f"reading {self.d['repo_name']} ({config.MODEL})")
                clean, row, _ = planner_agent.plan(self.d["goal"], describe_repo(self.d["repo"]), self.d["budget_usd"],
                                                   refresh_id=self.id)
                problems = clean.pop("problems", [])
                self.spend(row["usd"], what="planner")
            if "the task graph has a cycle" in problems:
                raise RunError("the planner produced a task graph with a cycle")
            with self.lock:
                self.d["plan_summary"] = clean["summary"]
                self.d["problems"] = problems
                self.d["nodes"] = [_new_node(n) for n in clean["nodes"]]
                self.d["order"] = clean["order"]
            for p in problems:
                self.event("plan_problem", p, level="warn")
            self.event("plan", f"{len(clean['nodes'])} tasks planned: {clean['summary']}")
            self.set_state("plan_ready")
            if self.d.get("auto_run"):
                self.approve()
        except (BudgetExceeded, ModelCallFailed, RunError, worktrees.GitError) as e:
            self.event("error", f"planning failed: {e}", level="error")
            self.set_state("failed", f"Planning failed: {e}")
        except Exception as e:  # the page must show it, not hang on "planning"
            traceback.print_exc()
            self.event("error", f"planning failed: {type(e).__name__}: {e}", level="error")
            self.set_state("failed", f"Planning failed: {type(e).__name__}: {e}")

    # ---------- running ----------

    def approve(self):
        with self.lock:
            if self.d["state"] != "plan_ready":
                raise RunError(f"the run is {self.d['state']}, not waiting for approval")
            if not self.d.get("integration"):
                path = self.wdir / self.id / "_integration"
                branch = f"lucidity/{self.id}"
                worktrees.add(self.d["repo"], path, branch, self.d["base_commit"])
                self.d["integration"] = {"path": str(path), "branch": branch}
            self.d["started"] = _now()
        self.event("run", "plan approved; running up to %d tasks at a time" % self.d["max_parallel"])
        self.set_state("running")
        self._ensure_loop()

    def _ensure_loop(self):
        if self.thread and self.thread.is_alive():
            return
        self.cancel.clear()
        self.thread = threading.Thread(target=self._loop, daemon=True, name=f"run-{self.id}")
        self.thread.start()

    def _loop(self):
        while True:
            with self.lock:
                if self.d["state"] != "running":
                    break
                try:
                    self._tick()
                except Exception as e:
                    traceback.print_exc()
                    self.event("error", f"scheduler error: {type(e).__name__}: {e}", level="error")
                    self.set_state("needs_you", f"Scheduler error: {e}")
                    break
            self.sample()
            time.sleep(TICK_S)
        self.save()

    def _tick(self):
        nodes = self.d["nodes"]
        by_id = {n["id"]: n for n in nodes}
        running = [n for n in nodes if n["state"] == "running"]
        over = self.d["spent_usd"] >= self.d["budget_usd"]
        for n in nodes:
            if n["state"] != "queued":
                continue
            if not all(by_id[d]["state"] in FINISHED for d in n["deps"]):
                continue
            if over or len(running) >= self.d["max_parallel"]:
                continue
            self._start_node(n)
            running.append(n)
        states = [n["state"] for n in nodes]
        if all(s in FINISHED for s in states):
            self._finish()
        elif not running:
            startable = [n for n in nodes if n["state"] == "queued"
                         and all(by_id[d]["state"] in FINISHED for d in n["deps"])]
            stuck_on_budget = any(n.get("needs_kind") == "run_budget" for n in nodes if n["state"] == "needs_you")
            if over and (startable or stuck_on_budget):
                self.d["needs_kind"] = "run_budget"
                left = len([n for n in nodes if n["state"] not in FINISHED])
                self.set_state("needs_you", f"The run spent ${self.d['spent_usd']:.2f} of its ${self.d['budget_usd']:.2f} budget "
                                            f"with {left} task{'s' if left != 1 else ''} not done.")
                self.event("needs_you", self.d["reason"], level="warn")
            elif "needs_you" in states:
                waiting = [n["id"] for n in nodes if n["state"] == "needs_you"]
                self.d["needs_kind"] = "node"
                self.set_state("needs_you", f"Waiting on you: {', '.join(waiting)}")

    def _finish(self):
        integ = self.d["integration"]
        self.d["merged_commit"] = worktrees.head(integ["path"])
        self.d["files_changed"] = worktrees.changed_files(integ["path"], self.d["base_commit"])
        self.event("run", f"all tasks done and merged into {integ['branch']}")
        self.set_state("done", f"Every task passed its checks and is merged into {integ['branch']}.")

    def _start_node(self, n):
        n["state"], n["phase"], n["reason"] = "running", "starting", ""
        n["needs_kind"] = None
        if not n.get("started"):
            n["started"] = self.elapsed()
        threading.Thread(target=self._work, args=(n,), daemon=True, name=f"{self.id}-{n['id']}").start()

    def _work(self, n):
        try:
            self._work_inner(n)
        except Exception as e:
            traceback.print_exc()
            with self.lock:
                n["state"], n["phase"], n["reason"], n["needs_kind"] = "needs_you", "", f"{type(e).__name__}: {e}", "error"
            self.event("error", f"{n['id']}: {type(e).__name__}: {e}", node=n["id"], level="error")
        finally:
            self.save()

    def _work_inner(self, n):
        if not n.get("worktree"):
            base = worktrees.head(self.d["integration"]["path"])
            path = self.wdir / self.id / f"{n['id']}-{n['attempt']}"
            branch = f"lucidity/{self.id}-{n['id']}-{n['attempt']}"
            worktrees.add(self.d["repo"], path, branch, base)
            with self.lock:
                n.update(worktree=str(path), branch=branch, start_commit=base)
            self.event("worktree", f"{n['id']}: worktree on {branch}", node=n["id"])
            weak = [m for m in contracts.evaluate(n["done_when"], path) if m["met"] is True]
            checkable = [c for c in n["done_when"] if c["kind"] != "rubric"]
            if checkable and len(weak) == len(checkable):
                n["weak"] = True
                self.event("weak_contract", f"{n['id']}: every check already passes before any work, so passing proves little",
                           node=n["id"], level="warn")
        while True:
            with self.lock:
                if self.cancel.is_set():
                    return self._stopped(n)
                if self.d["spent_usd"] >= self.d["budget_usd"]:
                    return self._needs(n, "run_budget", f"The run's ${self.d['budget_usd']:.2f} budget is spent.")
                n["round"] += 1
                rnd = n["round"]
                n["phase"] = "working"
                span = {"kind": "work", "round": rnd, "start": self.elapsed(), "end": None}
                n["spans"].append(span)
            self.event("round", f"{n['id']}: round {rnd} started", node=n["id"])
            remaining = max(0.0, n["budget_usd"] - n["spent_usd"])
            res = self.worker.run(n, rnd, self._prompt(n), n["worktree"], remaining,
                                  emit=lambda line, nid=n["id"]: self.event("activity", line, node=nid),
                                  cancelled=self.cancel.is_set)
            span["end"] = self.elapsed()
            self.spend(res.get("usd") or 0.0, n)
            files = worktrees.changed_files(n["worktree"], n["start_commit"])
            with self.lock:
                n["files"] = files
                n["reports"].append({"round": rnd, "text": (res.get("report") or "")[:2000]})
            if self.cancel.is_set():
                return self._stopped(n)
            # the gate
            with self.lock:
                n["phase"] = "checking"
                span = {"kind": "check", "round": rnd, "start": self.elapsed(), "end": None}
                n["spans"].append(span)
            mech = contracts.evaluate(n["done_when"], n["worktree"])
            if res.get("error"):
                verdict = {"verdict": "fail", "reasons": [f"the worker stopped with an error: {res['error']}"],
                           "conditions": mech, "usd": 0.0, "by": "program"}
            else:
                try:
                    verdict = gate.grade(n, mech, res.get("report"), worktrees.diff(n["worktree"], n["start_commit"]),
                                         history=n["checks"], refresh_id=self.id)
                except (BudgetExceeded, ModelCallFailed) as e:
                    verdict = {"verdict": "needs_you", "reasons": [f"the checker could not run: {e}"], "conditions": mech,
                               "usd": 0.0, "by": "none"}
            span["end"] = self.elapsed()
            span["ok"] = verdict["verdict"] == "pass"
            if verdict["usd"]:
                self.spend(verdict["usd"], n, what="checker")
            with self.lock:
                n["checks"].append({"round": rnd, "s": self.elapsed(), **verdict})
            self.event("check", f"{n['id']} round {rnd}: {verdict['verdict'].upper().replace('_', ' ')}"
                       + (f" — {verdict['reasons'][0]}" if verdict["reasons"] else ""),
                       node=n["id"], level={"pass": "ok", "fail": "warn"}.get(verdict["verdict"], "error"))
            if verdict["verdict"] == "pass":
                return self._merge(n)
            if verdict["verdict"] == "needs_you":
                return self._needs(n, "checker", "; ".join(verdict["reasons"]) or "The checker wants a person to look.")
            if n["spent_usd"] >= n["budget_usd"]:
                return self._needs(n, "budget", f"Spent ${n['spent_usd']:.2f} of its ${n['budget_usd']:.2f} budget "
                                                f"and the check still fails.")
            if rnd >= n["max_rounds"]:
                return self._needs(n, "rounds", f"Still failing after {rnd} round{'s' if rnd > 1 else ''}.")

    def _prompt(self, n):
        lines = [f"You are doing one task of a larger plan, in a git worktree of the {self.d['repo_name']} repo.",
                 "Work only inside this folder. Do not commit, merge, push or change git settings: Lucidity commits "
                 "and merges your work after an independent check.", "",
                 f"OVERALL GOAL: {self.d['goal']}", "", contracts.contract_text(n)]
        if n["checks"]:
            last = n["checks"][-1]
            lines += ["", f"Your round {last['round']} was checked and did NOT pass:"]
            lines += [f"- {r}" for r in last["reasons"][:6]]
            lines.append("Fix exactly that, then check again.")
        lines += ["", "When you are finished, reply in two sentences: what you changed, and whether the conditions pass."]
        return "\n".join(lines)

    def _merge(self, n):
        with self.lock:
            n["phase"] = "merging"
        sha = worktrees.commit_all(n["worktree"], f"{n['id']}: {n['title']}")
        with self.merge_lock:
            res = worktrees.merge(self.d["integration"]["path"], n["branch"],
                                  f"Merge {n['id']} ({n['title']}): checks passed")
        if not res["ok"]:
            what = ", ".join(res["conflicts"]) or res["error"] or "unknown"
            # the work is fine but no longer fits; the retry starts again on top of the latest merge
            return self._needs(n, "conflict", f"Checks passed but the merge conflicted in {what}.")
        worktrees.remove(self.d["repo"], n["worktree"])
        with self.lock:
            n.update(state="done", phase="", reason="", merged_commit=res["commit"], commit=sha,
                     finished=self.elapsed(), worktree=None)
        self.event("merge", f"{n['id']} merged into {self.d['integration']['branch']} ({len(n['files'])} files)",
                   node=n["id"], level="ok")
        self.sample(force=True)

    def _needs(self, n, kind, reason):
        with self.lock:
            n.update(state="needs_you", phase="", reason=reason, needs_kind=kind)
        self.event("needs_you", f"{n['id']}: {reason}", node=n["id"], level="error")
        self.sample(force=True)

    def _stopped(self, n):
        with self.lock:
            n.update(state="stopped", phase="", reason="stopped")
        self.event("stopped", f"{n['id']} stopped", node=n["id"], level="warn")

    # ---------- your actions ----------

    def act(self, action, node=None, amount=0.0):
        amount = float(amount or 0)
        if amount < 0 or amount > config.MAX_RUN_USD:
            raise RunError(f"amount must be between $0 and ${config.MAX_RUN_USD:.2f}")
        if action == "approve":
            return self.approve()
        if action == "stop":
            self.cancel.set()
            with self.lock:
                for n in self.d["nodes"]:
                    if n["state"] == "queued":
                        n["state"] = "stopped"
            self.event("run", "stopped by you", level="warn")
            return self.set_state("stopped", "Stopped by you.")
        if action == "raise_budget":
            if self.d["budget_usd"] + amount > config.MAX_RUN_USD:
                raise RunError(f"a run's budget can't go over ${config.MAX_RUN_USD:.2f} (LUCIDITY_MAX_RUN_USD)")
            with self.lock:
                self.d["budget_usd"] = round(self.d["budget_usd"] + amount, 2)
                for n in self.d["nodes"]:
                    if n["state"] == "needs_you" and n.get("needs_kind") == "run_budget":
                        n.update(state="queued", reason="", needs_kind=None)
            self.event("you", f"run budget raised by ${amount:.2f} to ${self.d['budget_usd']:.2f}")
            return self._resume()
        if action == "resume":
            if self.d["state"] != "stopped":
                raise RunError(f"the run is {self.d['state']}, not stopped")
            self.event("you", "resumed")
            return self._resume()
        n = self.node(node)
        if action in ("retry", "add_budget"):
            if n["state"] not in ("needs_you", "stopped"):
                raise RunError(f"{n['id']} is {n['state']}; only a task that needs you or was stopped can be retried")
            with self.lock:
                if action == "add_budget":
                    if amount <= 0:
                        raise RunError("say how much to add")
                    if self.d["spent_usd"] + amount > config.MAX_RUN_USD:
                        raise RunError(f"that would take the run past ${config.MAX_RUN_USD:.2f} (LUCIDITY_MAX_RUN_USD)")
                    n["budget_usd"] = round(n["budget_usd"] + amount, 2)
                    self.d["budget_usd"] = round(max(self.d["budget_usd"], self.d["spent_usd"] + amount), 2)
                n["max_rounds"] = max(n["max_rounds"], n["round"] + 1)
                if n.get("needs_kind") == "conflict" or not n.get("worktree"):
                    if n.get("worktree"):
                        worktrees.remove(self.d["repo"], n["worktree"])
                    n.update(worktree=None, attempt=n["attempt"] + 1)
                n.update(state="queued", reason="", needs_kind=None)
            self.event("you", f"{n['id']}: " + (f"budget +${amount:.2f}, " if action == "add_budget" else "") + "one more round")
            return self._resume()
        if action == "skip":
            if n["state"] in ("done", "running"):
                raise RunError(f"{n['id']} is {n['state']} and can't be skipped")
            with self.lock:
                if n.get("worktree"):
                    worktrees.remove(self.d["repo"], n["worktree"])
                n.update(state="skipped", reason="skipped by you", worktree=None, needs_kind=None)
            self.event("you", f"{n['id']} skipped; tasks after it run without it", node=n["id"], level="warn")
            return self._resume()
        raise RunError(f"unknown action {action}")

    def _resume(self):
        if self.d["state"] in ("needs_you", "stopped", "running"):
            self.cancel.clear()
            with self.lock:
                for n in self.d["nodes"]:
                    if n["state"] == "stopped":
                        n["state"] = "queued"
            self.set_state("running")
            self._ensure_loop()


def _actions_for(n):
    kind = n.get("needs_kind")
    if kind == "budget":
        return ["add_budget", "skip"]
    if kind == "run_budget":
        return ["raise_budget", "skip"]
    return ["retry", "skip"]


def _new_node(n):
    return {**n, "state": "queued", "phase": "", "reason": "", "needs_kind": None, "round": 0, "attempt": 1,
            "spent_usd": 0.0, "started": None, "finished": None, "spans": [], "checks": [], "reports": [],
            "files": [], "worktree": None, "branch": None, "start_commit": None, "weak": False}


def describe_repo(repo, limit=4000):
    """What the planner sees: the file list and the README's opening. Data, not instructions."""
    from ..repomap import _walk
    files, total = _walk(Path(repo))
    readme = next((Path(repo) / f for f in ("README.md", "README.rst", "README.txt", "README") if (Path(repo) / f).is_file()), None)
    text = f"Repo {Path(repo).name}, {total} files:\n" + "\n".join(files[:300])
    if readme:
        text += "\n\nREADME:\n" + readme.read_text(encoding="utf-8", errors="replace")[:limit]
    return text


# ---------- the registry the server uses ----------

def _new_id():
    return datetime.now().strftime("%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:4]


def create(goal, repo=None, budget_usd=None, worker="demo", max_parallel=3, auto_run=False, demo_speed=None):
    goal = re.sub(r"\s+", " ", (goal or "").strip())
    if worker == "demo":
        w = DemoWorker(demo.Scenario(), speed=demo_speed)
        goal = goal or w.scenario.goal
        budget_usd = w.scenario.budget_usd if budget_usd in (None, "") else budget_usd
    else:
        w = LIVE.get(worker)
        if w is None:
            raise RunError(f"unknown worker {worker!r}")
        ok, why = w.available()
        if not ok:
            raise RunError(f"{w.label}: {why}")
        if not config.has_key():
            raise RunError("Planning your own goal needs OPENAI_API_KEY in .env (the planner and checker use "
                           f"{config.MODEL}). Demo mode works without one.")
    if not goal or len(goal) < 8:
        raise RunError("describe the goal in a sentence")
    if len(goal) > 2000:
        raise RunError("keep the goal under 2,000 characters")
    try:
        budget_usd = round(float(budget_usd if budget_usd not in (None, "") else 1.0), 2)
    except (TypeError, ValueError):
        raise RunError("budget must be a number of dollars") from None
    if not 0 < budget_usd <= config.MAX_RUN_USD:
        raise RunError(f"budget must be more than $0 and at most ${config.MAX_RUN_USD:.2f} (LUCIDITY_MAX_RUN_USD)")
    if not worktrees.available():
        raise RunError("git is not installed or not on PATH; Lucidity needs it to give each task its own worktree")
    max_parallel = max(1, min(6, int(max_parallel or 3)))
    rid = _new_id()
    if worker == "demo":
        repo = demo.prepare_repo(config.STATE_DIR / "demo" / rid)
    else:
        repo = Path(str(repo or "").strip().strip('"')).expanduser()
        if not str(repo) or not repo.is_dir():
            raise RunError("pick a folder that exists")
        if not worktrees.is_repo(repo):
            raise RunError(f"{repo} is not a git repository")
        repo = worktrees.toplevel(repo)
        if not worktrees.has_commits(repo):
            raise RunError(f"{repo.name} has no commits yet; commit once so tasks have something to branch from")
    data = {"id": rid, "goal": goal, "repo": str(repo), "repo_name": Path(repo).name, "mode": "demo" if worker == "demo" else "live",
            "worker": worker, "worker_label": w.label, "model": config.MODEL, "state": "planning", "reason": "",
            "needs_kind": None, "created": _now(), "started": None, "finished": None, "updated": _now(),
            "budget_usd": budget_usd, "spent_usd": 0.0, "spend_by": {}, "max_parallel": max_parallel,
            "auto_run": bool(auto_run), "base_commit": worktrees.head(repo), "integration": None,
            "plan_summary": "", "problems": [], "nodes": [], "order": [], "events": [], "samples": [],
            "elapsed_s": 0}
    run = Run(data, w)
    with _registry_lock:
        _registry[rid] = run
    run.event("goal", goal)
    run.sample(force=True)
    run.plan_async()
    return run


def get(rid):
    with _registry_lock:
        run = _registry.get(rid)
    if run:
        return run
    if not re.fullmatch(r"[0-9a-z-]{6,40}", rid or ""):
        return None
    p = runs_dir() / f"{rid}.json"
    if not p.exists():
        return None
    run = _load(p)
    with _registry_lock:
        _registry.setdefault(rid, run)
    return _registry[rid]


def _load(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    w = DemoWorker(demo.Scenario()) if data["worker"] == "demo" else LIVE.get(data["worker"])
    run = Run(data, w)
    if data["state"] in ("planning", "running"):
        # the server restarted under it; nothing is running any more
        for n in data["nodes"]:
            if n["state"] == "running":
                n.update(state="stopped", phase="", reason="Lucidity restarted while this task ran")
        data["state"] = "failed" if data["state"] == "planning" else "stopped"
        data["reason"] = "Lucidity restarted while this run was in progress."
    return run


def list_runs(limit=30):
    seen = {}
    if runs_dir().exists():
        for p in sorted(runs_dir().glob("*.json"), reverse=True)[:limit * 2]:
            rid = p.stem
            run = get(rid)
            if run:
                seen[rid] = run
    with _registry_lock:
        for rid, run in _registry.items():
            seen.setdefault(rid, run)
    out = []
    for run in seen.values():
        d = run.d
        out.append({"id": d["id"], "goal": d["goal"], "repo_name": d["repo_name"], "mode": d["mode"], "state": d["state"],
                    "worker": d["worker"], "created": d["created"], "spent_usd": d["spent_usd"], "budget_usd": d["budget_usd"],
                    "tasks": len(d["nodes"]), "done": sum(n["state"] == "done" for n in d["nodes"])})
    out.sort(key=lambda r: r["created"], reverse=True)
    return out[:limit]


def delete(rid):
    run = get(rid)
    if not run:
        raise RunError("no such run")
    if run.d["state"] in ("planning", "running"):
        raise RunError("stop the run before deleting it")
    repo = run.d["repo"]
    for n in run.d["nodes"]:
        if n.get("worktree"):
            worktrees.remove(repo, n["worktree"])
    if run.d.get("integration"):
        # the integration branch stays in your repo (it is the run's result); only its folder goes
        worktrees.remove(repo, run.d["integration"]["path"])
    shutil.rmtree(work_dir() / rid, ignore_errors=True)
    if run.d["mode"] == "demo":
        shutil.rmtree(config.STATE_DIR / "demo" / rid, ignore_errors=True)
    (runs_dir() / f"{rid}.json").unlink(missing_ok=True)
    with _registry_lock:
        _registry.pop(rid, None)
