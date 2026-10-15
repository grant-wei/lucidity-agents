# Dev error review and baseline

Reviewed `python evals/score.py --split dev --misses` and inspected `complaintkit/prompt.py`, `complaintkit/labels.py`, and `evals/score.py`. No held-out examples or miss output were inspected; held-out was run only in aggregate with `python evals/score.py` as a comparison baseline.

## Dev baseline and error patterns

On dev (144 rows), accuracy is 0.7569. Per-product F1: credit_reporting 0.8511, debt_collection 0.7179, credit_card 0.7925, checking_savings 0.8163, money_transfer 0.6667, mortgage 0.9565.

The dev misses expose several recurring patterns:
- `unknown` answers (notably collection agencies/debt collection and gift/prepaid cards) because the parser recognizes only a small set of exact-ish keywords, and the prompt does not constrain the answer to the six supported labels.
- Money-transfer complaints involving checks, wires, and scams are often returned as checking/savings; the parser's `transfer` keyword cannot resolve product intent when the model does not use it.
- Checking/savings complaints can mention a credit card, and collection-versus-credit-report complaints commonly mention both a debt and a credit report. The current parser's first-matching-keyword ordering can override the complaint's primary product.

## Held-out baseline (aggregate only; comparison point)

The mandated held-out score run returned accuracy 0.7986. Per-product F1: credit_reporting 0.8163, debt_collection 0.7442, credit_card 0.8800, checking_savings 0.8750, money_transfer 0.6667, mortgage 0.9796. No held-out examples were used to identify changes or tune.

## Most promising component

Changing both prompt and parser is most promising: the prompt should explicitly enumerate the six product labels and require one exact label, reducing free-form/unparseable answers and focusing the model on the primary product; parser improvements should accept label variants/aliases and avoid fixed-order matching when answers mention multiple products. Prompt-only cannot reliably fix existing unknown free-text variants, while parser-only cannot improve model decisions on ambiguous complaint content.
