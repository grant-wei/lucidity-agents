# Tokenomics

From `python evidence/tokenomics.py` on 2026-10-15: every finished live run on a table so far, with the Built-in
worker on `gpt-6-luna` ($0.10 per million input tokens, $0.01 cached, $0.50 output).

| Run | Table | Model requests | Input tokens (cached) | Output tokens | Cost | Cost with no caching | Time |
|---|---|---|---|---|---|---|---|
| `1014-152204-72b0` | hoopkit | 83 | 241,701 (79%) | 9,616 | $0.0123 | $0.0290 | 173 s |
| `1014-152917-7373` | hoopkit | 118 | 336,382 (82%) | 12,149 | $0.0154 | $0.0397 | 182 s |
| `1014-160450-8077` | hoopkit | 216 | 543,967 (77%) | 20,412 | $0.0268 | $0.0646 | 372 s |
| `1014-161622-05e8` | hoopkit | 222 | 665,240 (80%) | 22,943 | $0.0303 | $0.0780 | 598 s |
| `1014-173225-96b1` | creditkit | 188 | 617,601 (81%) | 16,349 | $0.0258 | $0.0699 | 682 s |
| `1014-181424-b6f9` | fedkit | 214 | 1,212,096 (79%) | 19,882 | $0.0446 | $0.1312 | 175 s |
| `1015-075659-bee8` | breast_cancer | 28 | 77,286 (69%) | 3,420 | $0.0047 | $0.0094 | 49 s |
| `1015-095415-a7ca` | diabetes | 39 | 98,525 (73%) | 3,431 | $0.0055 | $0.0116 | 59 s |
| `1015-095516-b90e` | seattle_weather | 68 | 263,785 (82%) | 6,184 | $0.0100 | $0.0295 | 118 s |

9 runs. Median $0.0154 a run, most expensive $0.0446. Prompt caching cut the model bill by 63%.

| Runs a month per user | Per user | 100 users | 10,000 users |
|---|---|---|---|
| 5 at the median | $0.08 | $7.70 | $770 |
| 20 at the median | $0.31 | $30.80 | $3,080 |
| 100 at the median | $1.54 | $154.00 | $15,400 |
| 100 at the most expensive | $4.46 | $446.14 | $44,614 |

## Reading it

- A run is a planner call, three or four agents working in parallel, and a checker. Almost all of the cost is the
  agents reading code and score output back into their context, which is why most input tokens are cached.
- "Cost with no caching" prices the same token counts with caching off. It's computed from the logged counts, not a
  second run, so it shows what caching saves on these calls, not how a cache-free run would behave.
- These are model costs only. Lucidity runs on the user's own machine, so there's no server bill per user; at 10,000
  users the first real cost would be hosting, if it ever moved off the laptop.
- Guardrails keep the tail bounded: each run has a dollar cap ($1 by default), and `lucidity/guard.py` stops all model
  calls past 120 requests an hour. That cap fired twice while recording these runs, which is the guard working.
