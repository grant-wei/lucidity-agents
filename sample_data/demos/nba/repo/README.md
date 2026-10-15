# hoopkit

Predicts whether the home team wins an NBA game, using only what was known before tip-off. The
output is a probability, so it's scored the way a bettor or a forecaster would be scored.

```
python evals/score.py               # train on 2001-2013, score the 2014 and 2015 seasons (one JSON line)
python evals/score.py --split dev   # train on 2001-2012, score 2013: tune here
python -m pytest -q
```

- `hoopkit/features.py` decides what the model knows about a game. Its `Tracker` sees games in date
  order: `features(game)` is asked before the game, `update(game)` is told the result after. That's
  what keeps the future out; `tests/test_no_lookahead.py` checks it.
- `hoopkit/model.py` returns the model: anything scikit-learn-shaped with `fit` and `predict_proba`.
- `data/games.csv` holds 19,274 games (regular season and playoffs, 2000-01 to 2014-15): date,
  season, home and away team, and the final score. From FiveThirtyEight's NBA Elo data (CC BY 4.0).

Scores (lower log loss is better):

| | held-out log loss | accuracy |
|---|---|---|
| Always the home team's average win rate | about 0.67 | 0.60 |
| This repo as it stands (each team's win % so far this season, logistic regression) | 0.623 | 0.653 |
| FiveThirtyEight's Elo forecast | 0.608 | 0.658 |

Known gaps: early in a season every team sits near 0.5, because nothing carries over from last
season. Win % ignores margin of victory, strength of opponents, rest and travel. The features
aren't scaled, which matters for distance- and margin-based models (kNN, SVM).
