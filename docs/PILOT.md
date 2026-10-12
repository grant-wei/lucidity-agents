# Lucidity pilot

Thanks for trying this. It takes about 5 minutes to set up and then runs in a browser tab while you
work with Claude Code or Codex as usual. Use it for a few days, then answer the questions at the bottom.

## Install (5 minutes)

1. Clone the repo and follow steps 1–3 of the [README](../README.md). You need Python 3.10+ and an
   OpenAI API key in a `.env` file.
2. Start it in **local mode** so it reads your own sessions:

   macOS / Linux:
   ```
   LUCIDITY_DATA=local python app.py
   ```
   Windows PowerShell:
   ```
   $env:LUCIDITY_DATA="local"; python app.py
   ```
3. Leave the tab open. It refreshes every minute.

## What it reads

- Claude Code logs in `~/.claude/projects/` and Codex logs in `~/.codex/sessions/`.
- Only sessions active in the last 3 days, at most 25.
- It never writes to those folders and never sends anything to your agents.

## What gets sent to the model

- For each session that changed since the last refresh: the first thing you typed plus the **last 14
  events** (messages, commands, short tool output), cut to 600 characters each.
- Before anything is sent, API keys, tokens, passwords and private keys are replaced with
  `[REDACTED]`. If a secret shows up in a log, the card says so by kind only ("API key"), never the value.
- Unchanged sessions aren't sent again.
- The calls go to OpenAI with the key in your `.env`. Lucidity caps itself at **$0.50 a day** and 120
  requests an hour; past that it stops calling the model and shows a banner.

If a project is sensitive, don't run local mode while it's open, or point it elsewhere with
`CLAUDE_CONFIG_DIR` / `CODEX_HOME`.

## Turning it off

- Close the terminal running `python app.py` (or press Ctrl+C). Nothing keeps running in the background.
- To remove everything Lucidity saved: delete the repo's `logs/` and `state/` folders. They hold the usage
  log, traces, your Pause/Stop clicks, and cached triage results.
- To lower the spending cap: add `LUCIDITY_DAILY_USD_CAP=0.10` to `.env`.

## Questions afterwards

I'll ask these in a short chat or call. Rough answers are fine.

1. Before Lucidity, when an agent was waiting on you (a question or an approval), how long did it
   usually sit before you noticed?
2. With Lucidity open, how long did it take? Any specific time you remember?
3. Did it catch anything you would have missed: a session stuck in a loop, a "done" that wasn't, a
   leaked key, something else?
4. Was anything on the screen wrong? Which card, and what was really going on?
5. Did any claim or button confuse you?
6. Roughly how many agent sessions do you run at once on a normal day?
7. Would you keep it open next week? Why or why not?
8. Would you pay for it? If yes, about how much a month?
9. Can I quote you in a class report, by first name or anonymously?

Answers:

| Question | Answer |
|---|---|
| 1 | |
| 2 | |
| 3 | |
| 4 | |
| 5 | |
| 6 | |
| 7 | |
| 8 | |
| 9 | |
