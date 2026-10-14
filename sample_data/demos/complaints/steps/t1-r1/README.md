# complaintkit

Routes a consumer's complaint about a bank or lender to the team that owns the product: credit
reporting, debt collection, credit card, checking and savings, money transfer, or mortgage. Each
complaint goes to an LLM (`gpt-6-luna`), and the model's answer is turned into one label.

```
python evals/score.py                        # F1 per product and accuracy on the held-out split (one JSON line)
python evals/score.py --split dev --misses   # Tune on dev: shows every wrong label
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

Dev baseline and diagnosis: the `--split dev --misses` run reports 128/144 correct (88.89%). Errors
show two main patterns: overlapping products in narratives (for example checking-account fraud
mentions a credit card, or debt collection mentions credit reporting), and unsupported or broad
products (gift cards, PayPal, and store credit) that the fixed keyword parser maps to `unknown` or an
adjacent product. The prompt asks only for the product and does not constrain its answer; the parser
uses first matching keyword, with debt before credit reporting, making mixed answers order-sensitive.
Targeted dev-only opportunities are to ask for the closest of the six supported labels and clarify
how to distinguish the named product from incidental mentions; improve parser coverage/precedence
only for clear equivalent terms. Do not tune against held-out examples.

Tune on dev; reserve held-out for final scoring.
