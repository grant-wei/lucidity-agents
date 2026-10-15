# stockkit

Predicts whether an industry's stocks beat the typical industry next month, using only returns
known by the end of this month. The output is a probability, so it's scored the way a forecaster
would be scored.

```
python evals/score.py               # train on 1971-2016, score 2017 to August 2026 (one JSON line)
python evals/score.py --split dev   # train on 1971-2009, score 2010-2016: tune here
python -m pytest -q
```

- `stockkit/features.py` decides what the model knows about an industry. Its `Tracker` sees months
  in order: `features(industry)` is asked before a month, `update(month, returns)` is told that
  month's returns after. That's what keeps the future out; `tests/test_no_lookahead.py` checks it.
- `stockkit/model.py` returns the model: anything scikit-learn-shaped with `fit` and `predict_proba`.
- `data/returns.csv` holds 33,320 monthly returns (49 industry portfolios, value-weighted, January
  1970 to August 2026). From Kenneth French's Data Library, built from CRSP.

Each month about half the industries beat the median, so the label is close to a coin flip.

Scores (lower log loss is better):

| | held-out log loss | accuracy | spread |
|---|---|---|---|
| A coin flip (always 0.5) | 0.6931 | 0.50 | 0 |
| This repo as it stands (last month's and last year's return, logistic regression) | 0.6933 | 0.514 | 0.76% a month |

spread is the average monthly return of the 10 industries the model likes most minus the 10 it
likes least. It can be positive while log loss is worse than a coin flip: the ranking is a little
right, the probabilities are overconfident.

Known gaps: features are raw returns, not ranked or scaled across industries, which matters for
distance- and margin-based models (kNN, SVM). Nothing about volatility, longer momentum or
reversal. Industry momentum was a documented effect in the 1990s; whether it survives after 2016
is what the held-out years test.
