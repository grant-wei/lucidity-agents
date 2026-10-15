"""The prompt sent to the model for each complaint."""

PROMPT = """Classify the consumer's complaint by the financial product or service primarily at issue.
Choose exactly one category from this taxonomy. Reply with only the category name shown:
credit card, mortgage, debt collection, credit report, checking, transfer.

Decision guide:
- Home loan, mortgage servicing, foreclosure, escrow, or mortgage payments -> mortgage
- A debt being pursued, collection calls/letters, a collector, or repossession tied to collection -> debt collection
- A credit report, bureau, score, inquiry, or an entry on a credit file -> credit report
- A credit/charge/retail card account, card billing, interest, purchases, fees, or unauthorized card use -> credit card
- A bank deposit account (checking or savings), opening/closing it, deposits, withdrawals, checks, or account servicing -> checking
- Sending/moving money or payments between people, businesses, or institutions, such as wires, Zelle, PayPal, or remittances -> transfer

Distinguish similar cases: a collector pursuing payment is debt collection, but an inaccurate bureau file or score is credit report. A credit card is credit card; a checking/debit deposit account is checking. A payment service is transfer unless the central issue is a bank deposit account. Classify by the central issue, not every product mentioned. Common terms include collections, debt, credit bureau/report, bank account, debit card, wire, Zelle, and PayPal.

Complaint:
{text}

Category name only:"""


def build(text):
    return PROMPT.format(text=text)
