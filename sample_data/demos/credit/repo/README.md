# creditkit

Predicts whether a credit-card customer misses next month's payment, from six months of account
history. The output is a probability, so it's scored the way a lender's risk model would be scored.

```
python evals/score.py               # train on train + dev customers, score the held-out ones (one JSON line)
python evals/score.py --split dev   # train on train customers, score dev: tune here
python -m pytest -q
```

- `creditkit/features.py` decides what the model knows about a customer: one list of numbers per
  customer, in `NAMES` order.
- `creditkit/model.py` returns the model: anything scikit-learn-shaped with `fit` and `predict_proba`.
- `data/customers.csv` holds 30,000 customers of a Taiwanese bank (April to September 2005): credit
  limit, education, monthly repayment status, bills and payments, and whether they defaulted in
  October. From the UCI Machine Learning Repository, "Default of Credit Card Clients" (CC BY 4.0).
- Customers are split by id: id % 5 == 0 is held out, 1 is dev, the rest train. Fixed, never reshuffled.
- Sex, marital status and age are in the data but may not feed the decision, as under US
  fair-lending rules. `tests/test_fair_lending.py` fails if a feature changes with any of them.

Scores (lower log loss is better):

| | held-out log loss | AUC | accuracy |
|---|---|---|---|
| Always the average default rate (22%) | about 0.528 | 0.50 | 0.78 |
| This repo as it stands (credit limit and last month's status, logistic regression) | 0.472 | 0.719 | 0.812 |

Known gaps: only two of the 21 allowed columns are used. Bills and payments are ignored, and so is
the repayment trend over six months. Nothing is scaled, which matters for distance- and
margin-based models (kNN, SVM).
