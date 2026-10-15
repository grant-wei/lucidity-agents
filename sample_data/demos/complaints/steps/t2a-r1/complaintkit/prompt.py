"""The prompt sent to the model for each complaint."""

PROMPT = """Identify the single financial product/service that is the main subject of this consumer complaint. Classify the issue itself, not every product mentioned. Choose exactly one category and output only its canonical answer label.

- credit card — credit/charge/store cards, card accounts or billing, card purchases, and gift or prepaid cards. Output: credit card
- mortgage — home mortgage or home-equity loan, mortgage servicing, escrow, foreclosure, or forbearance. Output: mortgage
- debt collection — collection agencies or creditors trying to collect, collection calls/notices, debt validation or disputes about whether an alleged debt is owed, and debt-related repossession. Output: debt collection
- credit reporting — credit bureau reports/files/scores, inquiries, tradelines, and disputes about information furnished to a bureau. Output: credit report
- checking/savings — deposit accounts and their servicing, including checking, savings, debit cards, deposits, withdrawals, overdrafts, and account access. Output: checking
- money transfer — sending/receiving funds, wire transfers, remittances, payment apps/services (e.g. Zelle, PayPal, Venmo), and person-to-person payments. Output: money transfer

Distinguish the complaint's actual subject: if the main problem is a collector pursuing payment or validating a debt, choose debt collection even if the debt also appears on a credit report. If the main problem is correcting bureau-file information or inquiries, choose credit reporting. Use credit card for a credit-card account or purchase; checking for a bank deposit/debit account; money transfer for the payment/transfer service. Do not classify by incidental mentions or legal phrases alone.

Complaint:
{text}

Output exactly one of: credit card, mortgage, debt collection, credit report, checking, money transfer."""


def build(text):
    return PROMPT.format(text=text)
