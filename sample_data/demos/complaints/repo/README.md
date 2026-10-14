# complaintkit

Routes a consumer's complaint about a bank or lender to the team that owns the product: credit
reporting, debt collection, credit card, checking and savings, money transfer, or mortgage. Each
complaint goes to an LLM (`gpt-6-luna`), and the model's answer is turned into one label.

```
python evals/score.py                        # F1 per product and accuracy on the held-out split (one JSON line)
python evals/score.py --split dev --misses   # tune on dev: shows every wrong label
python -m pytest -q
```

- `complaintkit/prompt.py` is the prompt sent for each complaint.
- `complaintkit/labels.py` turns the model's free-text answer into a label.
- `complaintkit/llm.py` makes the call and caches every answer under the repo's git directory, so
  re-scoring an unchanged prompt costs nothing. A changed prompt needs `OPENAI_API_KEY`.
- `data/dev.jsonl` is for tuning and `data/heldout.jsonl` is for scoring: 144 complaints each, 24 per
  product, all real complaints from the CFPB Consumer Complaint Database (public domain), with
  personal details already replaced by XXXX. `scripts/fetch_complaints.py` shows how they were drawn.

Every eval prints what its model calls cost (`cost.usd`, tokens, cache hits).

Known gaps: the prompt doesn't list the labels, so the model answers in its own words ("a
cryptocurrency account", "a HELOC") and the parser marks many answers `unknown`. The parser also
checks keywords in a fixed order, so an answer that names two products goes to whichever comes
first. The labels are what each consumer chose when filing, so some are debatable, especially debt
collection versus credit reporting.
