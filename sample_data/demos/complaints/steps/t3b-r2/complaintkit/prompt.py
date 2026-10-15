"""The prompt sent to the model for each complaint."""

PROMPT = """Classify the primary financial product or service involved in this complaint. Choose exactly ONE category from the list below and reply with only its canonical label (no explanation):
- credit card
- checking or savings
- money transfer
- mortgage
- debt collection
- credit reporting

Choose the category that matches the actual service/action the consumer wants fixed, not every product, company, or account mentioned. A product name, payment method, or mention of a debt/report by itself does not decide the label. If more than one applies, use the central complained-about action and requested remedy.

Category boundaries:
- credit card: servicing or use of a credit-card account: charges, billing, fees, interest, card transactions/disputes, or opening/closing the card account. A card used to pay for something is not enough; classify a separate transfer or underlying service instead.
- checking or savings: the bank deposit account itself: opening, access/login, closure, account takeover, deposits, check deposits/holds, withdrawals, or the bank's handling of account funds. An unauthorized withdrawal from a checking account is checking or savings when the complaint is about account access or the bank's account handling; do not call it money transfer merely because money moved. Use money transfer only when sending/receiving/payment transaction service is itself the issue.
- money transfer: a payment or money-movement transaction/service (wire, Zelle, Cash App, PayPal, remittance, or similar) that was failed, delayed, misdirected, unauthorized, or not refunded. Use this when the transfer/payment is the disputed service, not just because a deposit account or card funded it. For check fraud schemes, use money transfer when the complaint is about sending money onward or the payment transaction, but use checking or savings for an ordinary rejected/held deposit or account servicing.
- mortgage: a home mortgage/home-equity loan and its origination or servicing, including payments, escrow, forbearance, foreclosure, or mortgage-loan servicing. Keep mortgage even when the mortgage company calls itself a debt collector or the complaint uses collection language, if the underlying issue is mortgage servicing/loan status.
- debt collection: a collector's effort to obtain payment on a debt, including collection calls/letters, validation, harassment, or stopping collection. Choose this when collection conduct or obtaining payment is the complaint, even if the debt is disputed, fraudulent, or also appears on a credit report. Do not choose credit reporting just because a collection account is mentioned.
- credit reporting: a credit bureau/report/score's handling of information, such as inaccurate items, inquiries, identity-theft entries, disputes, or failure to investigate/remove information. Choose this when the remedy sought is correction/removal of report information or bureau investigation, and the complaint is not primarily about a collector contacting or pursuing the consumer. A debt's presence on a report alone does not make the complaint debt collection.

Complaint:
{text}

Canonical label:"""


def build(text):
    return PROMPT.format(text=text)
