# Live runs on public tables

Each table was set up through Bring a CSV, then run once with the Built-in worker on `gpt-6-luna`, auto-run on,
three or four agents in parallel, $1 cap. Scores are on the locked test split, computed by Lucidity's own scorer
after the run (agents can only score the tune split). Run records are under `state/runs/` on the machine that ran them.

| Table | Rows | Predict | Split | Metric | Start | Goal | End | Winner (of families tried) | Cost | Time |
|---|---|---|---|---|---|---|---|---|---|---|
| `examples/breast_cancer.csv` | 569 | diagnosis (2 classes) | random rows | log loss | 0.2721 | 0.245 | **0.0962** | Regularized logistic regression (of 3; runner-up random forest 0.1112) | $0.0047 | 49 s |
| `examples/diabetes.csv` | 442 | progression_one_year (number) | random rows | RMSE | 76.84 | 69.15 | **54.75** | Regularized linear regression (of 4; runner-up random forest 57.21) | $0.0055 | 59 s |
| `examples/seattle_weather.csv` | 1,461 | weather (5 classes) | by date: test on 2015-03-15 to 2015-12-31 | log loss | 0.5031 | 0.453 | **0.4485** | Random forest (of 3; boosted trees 0.4959 and logistic regression missed the goal after 2 rounds) | $0.0100 | 118 s |
| wine (uploaded through the Upload button, not shipped with the app) | 178 | cultivar (3 classes) | random rows | log loss | 0.5434 | 0.489 | **0.0705** | Agent's pick merged after 1 round (families offered: regularized logistic regression, random forest, boosted trees, SVM) | $0.0061 | 52 s |

Runs: breast cancer `1015-075659-bee8`, diabetes `1015-095415-a7ca`, weather `1015-095516-b90e`, wine `1015-111951-a487` (all 2026-10-15).

## Against ordinary regression

Since commit 712d01d every table also gets a benchmark: plain linear or logistic regression, no penalty, on every
numeric column, scored on the same test rows.

| Table | Plain regression | Agents' winner | Agents beat it? |
|---|---|---|---|
| Breast cancer | 0.2362 | 0.0962 | yes |
| Diabetes | 53.96 | 54.75 | **no** |
| Weather | 0.4344 | 0.4485 | **no** |
| Wine | 0.0953 | 0.0705 | yes |

On diabetes and weather the agents cleared the 10% goal but lost to the textbook model, which is why the composer now
offers to set the goal at the benchmark when the benchmark already clears it.

## Checked by hand afterwards

- Rerunning `python evals/score.py` in each merged result gives the same test score as the table above.
- `git diff` of each merge touches no file under `evals/` or `data/`.
- The same scorer run as an agent (`LUCIDITY_ROLE=agent`) refuses: "held-out scores are only shown to the referee".

## What the runs found

The first diabetes run failed every agent: the planner named the metric `held_out.rmse` while the scorer prints
`rmse`. Fixed in commit 33ef4ad (`contracts.metric_key`), with a test. The rerun also showed auto-run and a click
could approve the same plan twice; the same commit makes approval happen once.

Weather is the honest case: two of three families never reached the goal, and only the random forest cleared it,
by a small margin. Testing on the newest rows is harder than a random split, which is the point of splitting by date.
