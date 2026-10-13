from invoicekit import FIELDS, extract
from invoicekit.fields.money import parse_amount

SAMPLE = """Lumen Print Works
19 Market Square, Springfield

INVOICE
Invoice No: INV-2041
Invoice Date: 2026-03-14
Terms: Net 30

Total Due: $1,234.50
"""


def test_every_field_is_returned():
    assert set(extract(SAMPLE)) == set(FIELDS)


def test_plain_dollar_amount():
    assert parse_amount("$1,234.50") == "1234.50"


def test_nothing_found_is_none():
    out = extract("hello")
    assert out["invoice_date"] is None and out["total"] is None
