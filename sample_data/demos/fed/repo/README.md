# fedkit

Predicts whether the Federal Reserve raises its target interest rate next month, from what was
known at the end of this month. The output is a probability, scored the way a forecaster would be.

```
python evals/score.py               # train on 1985-2014, score 2015 onward (one JSON line)
python evals/score.py --split dev   # train on 1985-2004, score 2005-2014: tune here
python -m pytest -q
```

- `fedkit/features.py` decides what the model knows about a month: one list of numbers per month,
  in `NAMES` order, built only from that month and earlier ones.
- `fedkit/model.py` returns the model: anything scikit-learn-shaped with `fit` and `predict_proba`.
- `data/months.csv` holds 501 months, January 1985 to September 2026: the Fed's target rate (the
  top of its range since December 2008), end-of-month Treasury yields (3-month, 2-year, 10-year),
  and last month's unemployment and CPI inflation, since a month's figures come out the next month.
  All from FRED (Federal Reserve Bank of St. Louis): DFEDTAR and DFEDTARU from the Federal Reserve
  Board, DGS3MO, DGS2 and DGS10 from the Treasury, UNRATE and CPIAUCNS from the Bureau of Labor
  Statistics. No October 2025 unemployment or CPI figure was published (the government shutdown),
  so September's carries forward. `scripts/prepare_months.py` rebuilds the file from the downloads.
- Months are split by year: 1985-2004 train, 2005-2014 dev, 2015 onward held out. The Fed raised
  rates in 21 of the 141 held-out months (the 2015-18 and 2022-23 hiking cycles, and 2026).
- `tests/test_no_lookahead.py` fails if a month's features read a later month or the answer.

Scores (lower log loss is better):

| | held-out log loss | AUC | accuracy |
|---|---|---|---|
| Always the average hike rate (about 1 month in 7) | about 0.421 | 0.50 | 0.85 |
| This repo as it stands (hiked this month, 10-year yield, logistic regression) | 0.462 | 0.611 | 0.851 |

Known gaps: the model ignores where short-term yields sit relative to the target, which is where
markets price the next move, and it ignores inflation and unemployment. Nothing is scaled, which
matters for distance- and margin-based models (kNN, SVM).
