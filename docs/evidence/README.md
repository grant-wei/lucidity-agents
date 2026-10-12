# Evidence

Screenshots come from the app running on the sample data with gpt-6-luna on 2026-10-12. Numbers come from
`scripts/measure_cost.py` and `evals/run_evals.py`, and both scripts can be re-run.

| File | Shows |
|---|---|
| `needs_you.png` | The Needs you box: two sessions waiting on an answer or approval, plus four flagged by rules |
| `runaway_explained.png` | A runaway session (321 repeated calls, $12.06 against a $5 cap), with the watchdog's explanation and suggested fix |
| `checker_not_verified.png` | The done checker running the tests and refusing a "done" claim: 2 tests failing and a placeholder test |
| `checker_verified.png` | The done checker confirming a real "done" |
| `secret_redacted.png` | Secrets in a transcript, named by kind only and redacted before any model call |
| `flow_view.png` | How it decided: one refresh as a graph, with plain-code steps and model calls marked |
| `safety_tests.png`, `safety_tests.txt` | The 22 safety tests (injection, secrets, command allowlist, spend breaker, uncited claims), then the full offline suite of 101 |
| `eval_table.png` | The Evals tab |
| `self_cost.png` | Lucidity's own spend meter and request count against its caps ($0.50 a day, 120 an hour) |
| `breaker_banner.png` | The breaker tripped (daily cap lowered to $0.05 for the shot), with the banner the page shows |
| `numbers.json` | Tokens and dollars per refresh, scaled per user per month and to 100 and 10,000 users |

`numbers.json` has two scaled blocks. `scaled_from_pilot` stays `[MISSING]` until the pilot measures how often a
user's sessions actually change. `scaled_assumed` uses a stated guess and is labeled as one.
