"""The prompt sent to the model for each complaint."""

PROMPT = """Classify the complaint by the financial product or service at the heart of the problem. Return exactly ONE canonical label from this list, with no explanation or other text:
credit report, debt collection, credit card, checking and savings, money transfer, mortgage.

Identify the specific action the consumer wants fixed. Classify that action, not the company name, legal citations, or incidental mentions of other products.

- credit report: the main problem is with a credit bureau/consumer report: inaccurate, obsolete, or fraudulent information displayed, or the bureau failed to investigate, correct, block, or remove it. The remedy sought is correction of the report or bureau's investigation.
- debt collection: a creditor or collector is pursuing, contacting, suing, threatening, or attempting to collect an alleged debt, or the issue is collection conduct, validation, or sale of a debt. This includes claims that the debt is not theirs, was paid, or is invalid. A debt appearing on a credit report does NOT make it credit report if the complaint is about a collector pursuing it; choose credit report only when the bureau/report itself is the problem. Examples: agencies trying to collect a disputed payday-loan balance = debt collection; Equifax refusing to remove an inaccurate account after a dispute = credit report.
- credit card: a credit-card account or a purchase charged to a credit card: charges, billing, interest, servicing, or card purchase disputes. Do not infer credit card just because a bank is named; identify the actual account.
- checking and savings: a bank/credit-union deposit account: account opening, closure or access; checks, deposits, cash, overdrafts, account fees, or the bank's handling of funds held in the account. A bank's incoming wire fee to its deposit-account customer is checking and savings. A debit/checking-account purchase issue is not credit card merely because a bank handled it.
- money transfer: a payment/remittance/transfer service that failed to send, receive, or return money, including payment apps and transfer scams. If the bank account is merely funding a failed transfer, choose money transfer; if the dispute is about the bank deposit account, its fee, check, or access, choose checking and savings.
- mortgage: servicing, payment, escrow, foreclosure, or modification of a home mortgage. Use mortgage for mortgage servicing even if the servicer calls itself a debt collector or late payment reporting is also mentioned.

For multiple products, choose the one responsible for the disputed action and remedy sought. Output one label only, exactly as written above.

Complaint:
{text}"""


def build(text):
    return PROMPT.format(text=text)
