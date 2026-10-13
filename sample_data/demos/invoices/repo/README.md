# invoicekit

Pulls six fields out of plain-text invoices: vendor, invoice number, invoice date, due date, total
and currency. Rule-based, no model calls, so it is cheap to run on every document.

```
python evals/score.py              # F1 per field on the held-out invoices (one JSON line)
python evals/score.py --split dev --misses   # tune on dev: shows every wrong field
python -m pytest -q tests
```

- `invoicekit/extract.py` calls one parser per field in `invoicekit/fields/`.
- `invoicekit/text.py` holds the helpers every parser shares.
- `data/dev` is for tuning, `data/heldout` is for scoring. Both are synthetic, made by
  `scripts/make_invoices.py`; every name and amount is made up.

Known gaps: only two date formats are read, the first line is assumed to be the vendor, "Subtotal"
is mistaken for the total, only dollars are recognised, and due dates are read only when written
out (payment terms like "Net 30" are ignored).
