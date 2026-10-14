"""The prompt sent to the model for each complaint."""

PROMPT = """Classify the financial product this customer complaint is about.
Answer with exactly one of these labels and nothing else:
credit_reporting, debt_collection, credit_card, checking_savings, money_transfer, mortgage

- credit_reporting: errors or disputes about what appears on a credit report.
- debt_collection: a collector trying to collect a debt, even if the debt shows on a credit report.
- money_transfer: sending or receiving money, including transfers into or out of a bank account.
- checking_savings: deposits, fees and access for a bank account.

Complaint:
{text}"""


def build(text):
    return PROMPT.format(text=text)
