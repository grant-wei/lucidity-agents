# What's left

- **Live runs with a real key.** The loop is tested end to end with the demo worker and with fake
  models (planner, checker, built-in worker) in temp git repos. A live run against a real repo with
  the course model, Claude Code and Codex hasn't been recorded yet; do one small run per worker and
  note the cost.
- **Codex budget.** The Codex CLI has no hard budget flag, so its spend is estimated from token
  counts (`LUCIDITY_CODEX_MODEL` sets the price) and enforced at the end of a round, not mid-round.
- **Resume after restart.** A run that was in progress when the server stopped is marked stopped,
  with its worktrees and branch kept. There is no "resume" button yet; start a new run.
- **Merge back.** The run ends with its work on `lucidity/<run-id>`. A button to open a PR or merge
  into your branch is not built; the page shows the `git diff` command instead.
- **Report.** `report.html` still describes the earlier monitor-first version (the planner as a
  recorded replay, the old Planner tab). It was left as is on purpose.
- **Leftovers from the old Planner tab.** `/api/replay`, `sample_data/replays/` and
  `scripts/record_replay.py` are no longer used by the page; remove them once the report stops
  describing the replay.
- **Old screenshots.** `docs/screenshots/*.png` other than `run-*.png` and `composer.png` show the old
  UI. Nothing links to them; they're kept in case the slides use them.
