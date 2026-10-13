# Lucidity

An orchestrator for coding agents that you can watch. Give it a goal and a git repo. It plans the
goal into tasks, each with a done-when contract and a budget, runs a coding agent on every task in
its own git worktree, and has a separate checker decide whether each task is really done. Nothing
merges without a pass. While it runs you see the task graph, progress and spend over time against
the budget, and a map of the repo showing which agents changed which modules. When a check keeps
failing or a budget hits its cap, the run stops that task and asks you.

![A demo run waiting on a decision: one task hit its budget](docs/screenshots/run-needs-you.png)

The demo above needs no API key: a bundled toy shop repo, a recorded plan and scripted agent edits.
Everything after the edits is real: the tests run, the checks pass or fail, the budgets bind and the
merges are real git merges.

## Quickstart (one command)

You need Python 3.10 or newer and git.

```
git clone https://github.com/grant-wei/lucidity-agents
cd lucidity-agents
python start.py          # Windows: py start.py
```

`start.py` makes a `.venv`, installs `requirements.txt` into it (first run only, about a minute) and
opens http://127.0.0.1:8765. Click **Run the demo**. In about two minutes you'll see:

1. the goal planned into 6 tasks with dependencies,
2. agents working up to 3 tasks at once, each in its own worktree,
3. one task fail its check, get the failure back, and pass on round 2,
4. another task hit its $0.15 budget and land in **Needs you**. Click **Add $0.15 and retry**,
5. every task merge into the run's branch, and the progress, spend and repo-map panels fill in.

If port 8765 is taken it says so; pick another with `LUCIDITY_PORT=8800 python start.py`
(PowerShell: `$env:LUCIDITY_PORT="8800"; py start.py`). Set `LUCIDITY_NO_BROWSER=1` to skip opening
a browser, and `LUCIDITY_DEMO_SPEED=4` to play the demo four times faster.

Prefer to set it up by hand? `python -m venv .venv`, install `requirements.txt` with the venv's pip,
then run `app.py` with the venv's Python.

## Point it at your own repo

1. Add a key. Copy `.env.example` to `.env` and set `OPENAI_API_KEY`. Lucidity looks for `.env` in
   this folder first, then the folder above it. `OPENAI_MODEL` is optional and defaults to `gpt-6-luna`.
   A `.env` that still holds the placeholder key is ignored.
2. Restart, pick who does the work, type a goal, and give the full path to a git repo with at least
   one commit:
   - **Built-in**: a small agent on your OpenAI key that can read, write and run allowlisted tests.
   - **Claude Code**: your `claude` CLI, headless, with a hard `--max-budget-usd` per round.
   - **Codex**: your `codex` CLI, sandboxed to the task's worktree.
3. Untick "Start as soon as the plan is ready" if you want to read the plan before any agent runs.

Your checkout is never touched. A run gets its own branch `lucidity/<run-id>` in a worktree under
`state/`, each task branches off that, and only work the checker passed is merged back into it. When
the run is done, the page shows the `git diff` command to review the branch; merging it into your own
branch (or deleting it) is up to you.

## How a run works

```
goal ─► plan ─► run tasks (parallel, each in a worktree) ─► check ─► merge ─► done
                       ▲                                     │
                       └──── failed: reasons go back ◄───────┘   (1 to 4 rounds, set per task)
                                                             └─► needs you
```

- **Plan.** The planner model gets the goal plus the repo's file list and README opening. It returns
  tasks with dependencies, a budget for each, and done-when conditions. Plain code then validates the
  graph before anything runs: a cycle is rejected, unknown dependencies are dropped, budgets that add
  up to more than the run's are scaled down, a test command off the allowlist becomes a judgment
  condition, and every task must have at least one condition a program can check.
- **Work.** A task starts when its dependencies have merged. The worker sees its task prompt and the
  contract, works only inside its worktree, and never commits, merges or pushes.
- **Check.** Conditions a program can check (a file exists, a test passes, a string is present) are
  run first by plain code, and a failure there is final whatever the worker's report says. Only
  conditions that need judgment go to the checker model, in a separate call with no tools that sees
  the contract, the program's results, the diff and the report, never the worker's reasoning.
- **Needs you.** A task stops and asks you when its checks fail every round, it spends its budget, its
  merge conflicts, or the checker wants a person. Other tasks keep going. You can add budget and
  retry, retry, or skip.

## What you see

- **Runs**: the goal composer up front and every past run below it.
- **A run**: the needs-you callout, the task graph (click a task for its prompt, contract and every
  check result), a per-round timeline, progress by task state over time, spend against the budget,
  the repo map shaded by how much agents changed each module, and a live activity feed.
- **Sessions, Session map, Trace, Evals**: Lucidity's monitor for agent sessions you started by hand
  in Claude Code or Codex. It shows synthetic sample sessions by default; `LUCIDITY_DATA=local` reads
  your own `~/.claude/projects` and `~/.codex/sessions`. With no key it shows a recorded triage of the
  samples.

![A finished demo run in dark mode](docs/screenshots/run-done-dark.png)

## What gets sent to which model

| Step | Goes to | What it sees |
|---|---|---|
| Planner | `OPENAI_MODEL` (default `gpt-6-luna`) | your goal, the repo's file list (up to 300 paths) and the first 4,000 characters of its README |
| Built-in worker | same | its task prompt and contract, plus the files it chooses to read in its worktree |
| Claude Code / Codex worker | your own CLI and account | its task prompt and contract; the CLI reads files in the worktree as it works |
| Checker | `OPENAI_MODEL` | the contract, the program's check results, the diff and the worker's report, redacted |
| Session monitor | `OPENAI_MODEL` | the last 14 events of each changed session, with keys, tokens and passwords redacted |
| Demo | nothing | the plan and edits are recorded; no model is called |

Text from workers and sessions is wrapped as data and the models are told never to follow it.

## Cost caps

- **Per run:** you set a budget when you start (default $1.00 for live runs). A run stops starting
  tasks when it's spent, and no run can be budgeted above `LUCIDITY_MAX_RUN_USD` (default $5.00),
  including budget you add later.
- **Per task:** each task gets a share of the run budget from the plan. Claude Code enforces it with
  `--max-budget-usd`; for the others Lucidity stops at the end of the round that crosses it.
- **Lucidity's own calls** (planner, checker, built-in worker, monitor): $0.50 a day and 120 requests
  an hour by default (`LUCIDITY_DAILY_USD_CAP`, `LUCIDITY_CALLS_PER_HOUR_CAP`). When that trips, no
  further call is made and the page says so. Raise it for real live runs.
- Every model call is logged with its token counts and cost to `logs/usage.jsonl`.

## Safety

- Tests run only through allowlisted runners (`pytest`, `python -m pytest`, `npm test`, `go test`,
  `cargo test`), without a shell, with a timeout.
- Workers can't touch your branch or push; merges happen only after a pass, into the run's branch.
- If a model reply never fits the expected shape, that call is marked failed (its cost still counts)
  and the task goes to you instead of passing.
- In the monitor, Pause / Stop / Let it run are recorded to `logs/actions.jsonl`; Lucidity never
  stops your hand-started agents itself.

## Tests and evals

```
.venv/Scripts/python -m pytest -q    # 126 tests, offline, no key needed (macOS/Linux: .venv/bin/python)
python evals/run_evals.py            # monitor evals: 30 labeled cases x 5 configurations x 3 runs, about $0.07
python smoke.py                      # one tiny model call, to check your key
```

The tests run the whole demo loop in temp git repos (plan, parallel work, a failing check that
recovers, a budget stop, add budget, merge) and the run API over HTTP.

## Layout

```
start.py              one-command launcher
app.py                local web server (standard library)
lucidity/orch/        the orchestrator: runs, worktrees, contracts, gate (checks), workers, demo, repo map
lucidity/agents/      planner, worker, checker and the session monitor's agents
lucidity/             config, model calls, cost, budget breaker, redaction, tracing
static/               the UI: index.html, style.css, app.js (runs), monitor.js (sessions)
sample_data/demo/     the toy repo and the recorded demo scenario
sample_data/          synthetic sessions, labels and the recorded triage for the monitor
evals/  tests/        monitor evals and the test suite
```

What's not done yet is in [TODO.md](TODO.md).
