"""The prompt sent to the model for each complaint."""

PROMPT = """Identify the single financial product or service at the center of this complaint.
Choose exactly one answer below and output ONLY that exact answer (no explanation):
- credit card
- mortgage
- debt collection
- credit report
- checking
- transfer

Use this decision tree:
1. Is the main issue a home loan, mortgage payment/servicing, escrow, foreclosure, or loan modification? Choose mortgage.
2. Is the main issue a collector contacting the consumer, seeking payment, validating/collecting a debt, or collection harassment? Choose debt collection. A debt collector may also report the debt; choose debt collection when the complaint is about collection activity or an unpaid debt being pursued.
3. Is the main issue what a credit bureau/report/file/score/inquiry says, or correcting/removing information with Equifax, Experian, or TransUnion? Choose credit report. Choose this when the complaint is about bureau reporting, even if the reported item is a collection; do not choose it merely because the complaint mentions a debt or credit report incidentally.
4. Is the main issue a credit, charge, or store-card account, its purchases, billing, fees, interest, or disputed transactions? Choose credit card.
5. Is the main issue a checking/savings/deposit bank or credit-union account, debit card, deposits, checks, withdrawals, or account access? Choose checking.
6. Is the main issue sending, receiving, or moving money through a payment service or between parties (for example wire, Zelle, PayPal, Cash App, remittance, or person-to-person payment)? Choose transfer.

For overlaps, classify the service whose action the consumer wants fixed: bureau accuracy/removal -> credit report; collection calls, validation, or attempts to collect -> debt collection. A bank debit/checking account problem is checking, while a standalone transfer/payment service or payment sent to another person is transfer. Use exactly one canonical label from the list above.

Complaint:
{text}

Answer with one label only:"""


def build(text):
    return PROMPT.format(text=text)
