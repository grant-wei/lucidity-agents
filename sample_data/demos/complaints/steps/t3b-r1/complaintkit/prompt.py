"""The prompt sent to the model for each complaint."""

PROMPT = """Classify the primary financial product or service involved in this complaint. Choose exactly ONE category from the list below and reply with only its canonical label (no explanation):
- credit card
- checking or savings
- money transfer
- mortgage
- debt collection
- credit reporting

Choose based on the main problem the consumer wants fixed, not merely a product, company, or account mentioned in passing. If multiple products are mentioned, classify the product/service whose action is being complained about.

Category boundaries:
- credit card: a credit-card account or issuer issue, including card charges, billing, fees, interest, disputes, or opening/servicing the card account. A credit card merely mentioned as payment method does not make it a credit-card complaint.
- checking or savings: a bank deposit account (checking, savings, or similar) issue, including account access/opening/closure, deposits, withdrawals, holds, or bank account servicing. Use this for a bank's handling of funds in a deposit account, not a transfer service merely because a bank account funded it.
- money transfer: sending, receiving, or moving money through a transfer/payment service or transaction (such as Zelle, PayPal, Cash App, wire, or electronic transfer), including failed, misdirected, delayed, or unauthorized transfers. Use this when the transfer/payment itself is the central issue rather than the underlying deposit account or card.
- mortgage: a home mortgage or home-equity loan/servicing issue, including payments, escrow, foreclosure, or loan modification. A mortgage mentioned only as a way to send/receive funds is not enough.
- debt collection: efforts to collect, validate, or stop collection of a debt, including collection calls, letters, repossession, or disputed collection activity. Use this when the central issue is a collector's attempt to obtain payment, even if the debt is also on a credit report.
- credit reporting: credit bureaus or a credit report/score, including inaccurate, fraudulent, or unauthorized information, inquiries, or failure to investigate/remove information. Use this when the requested remedy concerns what is reported or how a bureau handled a report, rather than a collector's collection conduct. A debt or collection entry appearing on a report alone does not make the issue debt collection.

Complaint:
{text}

Canonical label:"""


def build(text):
    return PROMPT.format(text=text)
