"""The prompt sent to the model for each complaint."""

PROMPT = """Classify the complaint by the financial product or service at the heart of the problem. Return exactly ONE label from this list, with no explanation or other text:
credit report, debt collection, credit card, checking and savings, money transfer, mortgage.

Choose by the core issue being complained about, not by every product or company mentioned. A complaint about a bank's handling of a credit-card purchase dispute is credit card; a dispute about a bank deposit, account opening/closure, fees, or access to a checking or savings account is checking and savings. A wire fee charged by a bank on an account is checking and savings, while a payment or transfer service (such as PayPal or Cash App) failing to send, receive, or return money is money transfer.

Important distinction:
- debt collection: a collector or creditor is contacting, suing, harassing, or attempting to collect/repossess for an alleged debt; also disputes about debt validation or collection conduct. Example: an agency demands payment for a disputed rental balance.
- credit report: the main complaint is that a credit bureau/consumer report contains inaccurate, obsolete, or fraudulent information, or that a bureau failed to investigate, correct, block, or remove it. Example: disputing an account or inquiry on a credit report. Mention of a debt or collection account alone does NOT make it debt collection: choose credit report when the requested remedy concerns what is displayed on the report. Conversely, choose debt collection when the complaint concerns collection attempts, even if the consumer says the debt is not theirs.

Use mortgage for servicing, payments, escrow, foreclosure, or modification of a home mortgage. Use credit card for a credit-card account, charges, billing, interest, or card dispute. Select the single best match; do not list multiple labels.

Complaint:
{text}"""


def build(text):
    return PROMPT.format(text=text)
