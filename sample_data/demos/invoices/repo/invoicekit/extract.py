"""One invoice's text in, its fields out. Each field has its own parser in fields/; a parser that
can't find its field returns None rather than guessing."""
from .fields import dates, money, numbers, terms, vendor

FIELDS = ["vendor", "invoice_number", "invoice_date", "due_date", "total", "currency"]


def extract(text):
    return {
        "vendor": vendor.vendor(text),
        "invoice_number": numbers.invoice_number(text),
        "invoice_date": dates.invoice_date(text),
        "due_date": terms.due_date(text),
        "total": money.total(text),
        "currency": money.currency(text),
    }
