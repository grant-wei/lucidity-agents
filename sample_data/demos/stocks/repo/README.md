# stockkit

Predicts whether an industry's stocks beat the typical industry next month, using only data
known by the end of this month. The output is a probability, so it's scored the way a forecaster
would be scored.

```
python evals/score.py               # train on 1971-2016, score 2017 to August 2026 (one JSON line)
python evals/score.py --split dev   # train on 1971-2009, score 2010-2016: tune here
python -m pytest -q
```

- `stockkit/features.py` decides what the model knows about an industry. Its `Tracker` sees months
  in order: `features(industry)` is asked before a month, `update(month, returns, info)` is told
  that month's returns and other data after. That's what keeps the future out; `tests/test_no_lookahead.py` checks it.
- `stockkit/model.py` returns the model: anything scikit-learn-shaped with `fit` and `predict_proba`.
- `data/returns.csv` holds 33,320 monthly returns (49 industry portfolios, value-weighted, January
  1970 to August 2026).
- `data/factors.csv` holds each month's Fama-French five factors (market, size, value,
  profitability, investment), momentum and the T-bill rate. One number per month, the same for
  every industry.
- `data/industry_info.csv` holds each industry's firm count, average firm size and book-to-market
  (high = cheap) each month, lagged so each was known by then. `scripts/prepare_factors.py` says
  how.
- All three come from Kenneth French's Data Library, built from CRSP. `stockkit.load_info()` reads
  the last two; the Tracker keeps them in `factors` and `info`.

Each month about half the industries beat the median, so the label is close to a coin flip.

Scores (lower log loss is better):

| | held-out log loss | accuracy | spread |
|---|---|---|---|
| A coin flip (always 0.5) | 0.6931 | 0.50 | 0 |
| Plain logistic regression on all 12 columns (returns, factors, size, firms, book-to-market) | 0.6932 | 0.514 | |
| This repo as it stands (last month's and last year's return, logistic regression) | 0.6933 | 0.514 | 0.76% a month |

spread is the average monthly return of the 10 industries the model likes most minus the 10 it
likes least. It can be positive while log loss is worse than a coin flip: the ranking is a little
right, the probabilities are overconfident.

Known gaps: features are raw returns, not ranked or scaled across industries, which matters for
distance- and margin-based models (kNN, SVM). Nothing about volatility, longer momentum or
reversal. The factor and industry data are loaded but unused: factor returns can't tell industries
apart on their own, but each industry's exposure to them (say, a rolling 60-month beta) can, and
size and book-to-market differ by industry already. Industry momentum was a documented effect in the 1990s; whether it survives after 2016
is what the held-out years test.
