"""The prompt sent to the model for each complaint."""

PROMPT = """Classify the primary financial product involved in this customer complaint.
Return exactly one supported label below, with no explanation or other text:
credit_reporting, debt_collection, credit_card, checking_savings, money_transfer, mortgage

Use the product/account at the center of the problem, not every product mentioned. Apply these boundaries:
- credit_reporting: inaccurate/missing information, inquiries, or accounts on a credit report, or a credit bureau's handling of a report dispute. If the complaint is about a creditor's own account (including a credit card) or a collector's conduct, use that product/debt_collection, not credit_reporting just because the FCRA, a credit report, or a bureau is cited.
- debt_collection: attempts to collect a debt, debt validation, collection calls/harassment, or repossession tied to debt collection. A collection account's appearance on a report does not make it credit_reporting when the requested remedy is stopping collection or resolving the debt. But a mortgage servicing/ownership/forbearance issue remains mortgage even if the servicer is called a debt collector.
- credit_card: credit-card account, billing, charges, purchase disputes, fraud, fees, or servicing. Store-branded revolving credit is credit_card. Prepaid, debit, and gift cards (including Visa/vanilla gift cards) are not checking_savings merely because they are called debit cards or bought at a bank; if the complaint centers on the card issuer, activation, balance, or card terms, classify as credit_card. A dispute with a bank about its own deposit account remains checking_savings.
- checking_savings: bank or credit-union deposit accounts, account opening/closure, deposits, returned/held checks, and ordinary bank account servicing or account access/security. A bank account takeover remains checking_savings even if transfers are involved, unless the complaint centers on a payment app/service or a specific transfer.
- money_transfer: sending/receiving funds, wires, remittances, payment apps or services such as PayPal/Cash App/Venmo, and associated transfer scams or access to funds in a payment-service wallet. A bank-deposited check or rejected bank deposit is ordinarily checking_savings, not money_transfer; classify as money_transfer only when the transfer/payment service or movement of funds itself is the central issue.
- mortgage: home mortgages, servicing, escrow, foreclosure, forbearance, and mortgage insurance, including disputes with a mortgage servicer.

Choose the one label that best captures the complaint's main problem and requested remedy. Never invent a label; output exactly one of the six labels above.

Complaint:
{text}"""


def build(text):
    return PROMPT.format(text=text)
