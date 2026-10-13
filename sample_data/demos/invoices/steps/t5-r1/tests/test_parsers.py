import pytest

from invoicekit.fields.dates import parse_date
from invoicekit.fields.money import currency, parse_amount, total
from invoicekit.fields.numbers import invoice_number


@pytest.mark.parametrize("raw", ["2026-03-14", "03/14/2026", "14.03.2026", "14 March 2026",
                                 "March 14, 2026", "Mar 14 2026"])
def test_every_date_format(raw):
    assert parse_date(raw) == "2026-03-14"


def test_unknown_date_is_none():
    assert parse_date("next Tuesday") is None


@pytest.mark.parametrize("raw, want", [("$1,234.50", "1234.50"), ("1.234,50 €", "1234.50"),
                                       ("EUR 12.000,00", "12000.00"), ("GBP 980.00", "980.00"),
                                       ("£75.25", "75.25")])
def test_amounts(raw, want):
    assert parse_amount(raw) == want


def test_total_skips_subtotal_and_reads_currency():
    text = "Subtotal 900,00 €\nVAT 180,00 €\nTOTAL 1.080,00 €\n"
    assert total(text) == "1080.00" and currency(text) == "EUR"


def test_invoice_number_keeps_its_letters():
    assert invoice_number("Invoice No: INV-2041\n") == "INV-2041"
    assert invoice_number("Inv #: PO9559-B\n") == "PO9559-B"
