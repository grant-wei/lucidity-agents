# Lucidity Agents

One screen for every coding agent you have running. Lucidity reads Claude Code and Codex session logs
on your machine and tells you which sessions are waiting on you, which are stuck or burning money,
and whether the ones that say "done" actually are.

It runs locally. By default it shows **sample data** (8 synthetic sessions), so you can try it without
any agents of your own.

## Run it (about 5 minutes)

You need Python 3.10 or newer and an OpenAI API key.

1. Clone the repo and enter it.

   ```
   git clone https://github.com/grant-wei/lucidity-agents
   cd lucidity-agents
   ```

2. Put your key in a `.env` file. Lucidity looks in the repo folder first, then the folder above it.
   **If your `.env` is already one folder above the repo, skip this step.** Otherwise copy the
   example and fill in the key:

   ```
   cp .env.example .env        # Windows PowerShell: copy .env.example .env
   ```

   `.env` needs `OPENAI_API_KEY=...`. `OPENAI_MODEL` is optional and defaults to `gpt-6-luna`.
   A `.env` that still holds the placeholder key is ignored, so a copied example never hides a real key one folder up.

3. Make a virtual environment and install.

   macOS / Linux:
   ```
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   Windows (PowerShell):
   ```
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

   If PowerShell blocks `Activate.ps1`, skip activation and call the venv's Python directly:
   `.venv\Scripts\python -m pip install -r requirements.txt`, then `.venv\Scripts\python app.py` in step 4.

4. Start it.

   ```
   python app.py
   ```

   It opens http://127.0.0.1:8765 in your browser. The page says "Reading your sessions…" until the
   first refresh finishes. That takes 20 to 40 seconds and costs
   a tenth to a fifth of a cent (two measured runs on the sample data). After that, unchanged sessions are skipped, so leaving it open is nearly free.

   If port 8765 is taken, it stops and says so. Pick another port:
   `LUCIDITY_PORT=8800 python app.py` (Windows PowerShell: `$env:LUCIDITY_PORT="8800"; python app.py`).

5. Optional: point it at your own sessions instead of the sample data.

   ```
   LUCIDITY_DATA=local python app.py          # Windows PowerShell: $env:LUCIDITY_DATA="local"; python app.py
   ```

   It reads `~/.claude/projects` and `~/.codex/sessions` (the last 3 days, up to 25 sessions).
   Only redacted tails of those logs are sent to the model; see "What gets sent" below.

To check the setup with one tiny model call: `python smoke.py`.

## What's on the screen

- **Sessions.** A "Needs you" box first (sessions waiting on an answer or an approval, flagged runaways,
  unverified "done" claims, leaked secrets), then a card per session. Every claim on a card cites the
  log events it's based on; click a chip to see the event.
- **How it decided.** The agent graph for the last refresh: which steps were plain code, which were model
  calls, what each one read and returned, and what it cost.
- **Planner replay.** A recorded run of the planner splitting a goal into tasks with done-when contracts,
  a worker doing them, and the checker verifying each one. It's a recording; sample mode never spawns agents.
- **Evals.** Accuracy, tokens and cost for 30 labeled cases under several configurations.

## The agents

| Agent | Model? | Job |
|---|---|---|
| Collector | no | Reads the session logs, counts tokens and dollars |
| Coordinator | no | Skips sessions whose change signature hasn't moved; batches the rest |
| Triage | yes | needs you / working / finished, with claims that must cite event ids |
| Watchdog detectors | no | Runaway loops and spend in the last hour (active sessions only), the same failure repeating |
| Watchdog explainer | yes | Only for newly flagged sessions: why, and pause / stop / let it run |
| Done checker | yes | Runs the task's tests (allowlisted runners only) and grades its done-when list |
| Planner | yes | Goal to task graph with contracts; plain code validates the graph |

Facts that a program can establish (an unanswered question, a tool call waiting for approval, a secret
in the output) are decided in plain code and override the model.

## Safety

- **Lucidity's own spending cap.** $0.50 a day and 120 model requests an hour by default
  (`LUCIDITY_DAILY_USD_CAP`, `LUCIDITY_CALLS_PER_HOUR_CAP`). When it trips, no model call is made
  and the page shows a banner.
- **What gets sent.** The last 14 events of each changed session, with keys, tokens and passwords
  redacted first. Transcript text is wrapped as data and the model is told never to follow it.
- **Commands.** The checker runs only test runners (`pytest`, `python -m pytest`, `npm test`,
  `go test`, `cargo test`), without a shell, with a 2-minute timeout.
- **Bad model output.** If a reply never fits the expected shape, that one call is marked failed in the trace
  (its cost is still counted), the refresh carries on, and plain-code checks like "waiting on you" still apply.
- **Actions.** Pause / Stop / Let it run are recorded to `logs/actions.jsonl`; Lucidity never stops
  your agents itself.

## Tests and evals

```
python -m pytest -q                 # 101 tests, offline, no key needed (~10 s)
python evals/run_evals.py           # 30 cases x 5 configurations x 3 runs, about $0.07 and 15 minutes
python scripts/run_refresh.py       # one refresh from the command line, state vs label per session
python scripts/record_replay.py     # re-record the planner replay (needs requirements-dev.txt)
```

## Layout

```
app.py                  local web server (standard library)
lucidity/               readers, redaction, cost, budget breaker, tracing
lucidity/agents/        coordinator, triage, watchdog, checker, planner, worker
static/index.html       the whole UI, one file
sample_data/            synthetic sessions, labels, task contracts, fixtures, the recorded replay
evals/                  eval cases, runner, results.json
tests/                  readers, cost, watchdog, server and safety tests
```

Lucidity started as a personal tool I used before this course. This repo is a clean rebuild for MGT 409.
