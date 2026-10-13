"""Make the synthetic invoices in data/ and their gold labels. Every name, number and amount is
made up. Seeded, so running it again gives the same files.

    python scripts/make_invoices.py"""
import json
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

VENDORS = [
    ("Northwind Office Supply", "USD"), ("Blue Heron Catering", "USD"), ("Granite Peak Logistics", "USD"),
    ("Lumen Print Works", "USD"), ("Copperfield Electrical", "USD"), ("Orchard Lane Bakery", "USD"),
    ("Harbor & Pine Legal", "USD"), ("Saltmarsh Design Studio", "USD"), ("Kestrel Software GmbH", "EUR"),
    ("Atelier Moreau SARL", "EUR"), ("Brightwater Analytics BV", "EUR"), ("Vela Componenti Srl", "EUR"),
    ("Thistle & Co. Ltd", "GBP"), ("Fenwick Joinery Ltd", "GBP"), ("Albion Courier Services", "GBP"),
]
CUSTOMERS = ["Riverside Dental Group", "Maple Street Cafe", "Oakridge Schools", "Pinecrest Hotel",
             "Summit Climbing Gym", "Larkspur Architects", "Tidewater Clinic", "Juniper Yoga Studio"]
STREETS = ["Industrial Way", "Mill Road", "Harbour Street", "Station Lane", "Market Square", "Elm Avenue"]
CITIES = {"USD": ["Springfield", "Riverton", "Fairview"], "EUR": ["Rotterdam", "Lyon", "Munich", "Bologna"],
          "GBP": ["Leeds", "Bristol", "York"]}
ITEMS = ["Consulting hours", "Printer toner", "Delivery", "Catering for 20", "Cable installation",
         "Software licence", "Design revisions", "Pastry tray", "Legal review", "Storage, monthly"]
DATE_FORMATS = {"USD": ["%m/%d/%Y", "%Y-%m-%d", "%B %d, %Y", "%b %d %Y", "%m/%d/%Y"],
                "EUR": ["%d.%m.%Y", "%d/%m/%Y", "%d %B %Y", "%Y-%m-%d"],
                "GBP": ["%d/%m/%Y", "%d %B %Y", "%d/%m/%Y", "%Y-%m-%d"]}


def money(amount, cur, rng):
    whole, cents = f"{amount:.2f}".split(".")
    us = f"{int(whole):,}.{cents}"
    eu = f"{int(whole):,}".replace(",", ".") + "," + cents
    if cur == "USD":
        return rng.choice([f"${us}", f"USD {us}", f"${us}"])
    if cur == "EUR":
        return rng.choice([f"{eu} €", f"EUR {eu}", f"€{eu}"])
    return rng.choice([f"£{us}", f"GBP {us}"])


def fmt_date(d, cur, rng):
    """US invoices write month first, European ones day first, so 04/05/2026 depends on who sent it."""
    return d.strftime(rng.choice(DATE_FORMATS[cur]))


def invoice_number(rng):
    n = rng.randint(1000, 9999)
    return rng.choice([f"INV-{n}", f"INV-{n}", f"{rng.choice([2025, 2026])}-{n:04d}", f"A-{n}{rng.randint(0, 9)}",
                       f"{n}", f"PO{n}-B"])


def one(rng):
    vendor, cur = rng.choice(VENDORS)
    issued = date(2026, 1, 5) + timedelta(days=rng.randint(0, 250))
    terms_kind = rng.choices(["net", "explicit", "receipt"], weights=[6, 3, 2])[0]
    if terms_kind == "net":
        days = rng.choice([15, 30, 30, 45, 60])
        due, terms = issued + timedelta(days=days), rng.choice([f"Net {days}", f"Net {days} days", f"NET{days}"])
    elif terms_kind == "explicit":
        due, terms = issued + timedelta(days=rng.choice([10, 14, 21, 30])), None
    else:
        due, terms = issued, rng.choice(["Due on receipt", "Payable upon receipt"])
    items = [(rng.choice(ITEMS), rng.randint(1, 12), rng.randint(15, 900) + rng.choice([0, 0.5, 0.25, 0.99]))
             for _ in range(rng.randint(1, 4))]
    sub = round(sum(q * p for _, q, p in items), 2)
    tax = round(sub * rng.choice([0.0, 0.06, 0.08, 0.2]), 2)
    total = round(sub + tax, 2)
    num = invoice_number(rng)
    customer = rng.choice(CUSTOMERS)
    addr = f"{rng.randint(2, 480)} {rng.choice(STREETS)}, {rng.choice(CITIES[cur])}"
    item_lines = [f"{d:<24}{q:>4}   {money(q * p, cur, rng)}" for d, q, p in items]
    m = lambda x: money(x, cur, rng)
    due_line = f"Payment due: {fmt_date(due, cur, rng)}" if terms is None else f"Terms: {terms}"
    layout = rng.choice("ABCD")
    if layout == "A":
        lines = [vendor, addr, "", "INVOICE", f"Invoice No: {num}", f"Invoice Date: {fmt_date(issued, cur, rng)}", due_line,
                 "", "Bill To:", customer, "", *item_lines, "", f"Subtotal: {m(sub)}", f"Tax: {m(tax)}",
                 f"Total Due: {m(total)}"]
    elif layout == "B":
        lines = ["INVOICE", f"From: {vendor}", addr, f"Bill to: {customer}", "",
                 f"Number: {num}    Date: {fmt_date(issued, cur, rng)}", due_line, "", *item_lines, "",
                 f"Subtotal {m(sub)}", f"VAT {m(tax)}", f"TOTAL {m(total)}"]
    elif layout == "C":
        lines = [f"*** {vendor.upper()} ***", addr, "Tax invoice", "", f"Inv #: {num}",
                 f"Issued: {fmt_date(issued, cur, rng)}", due_line, "", *item_lines, "",
                 f"Sub-total: {m(sub)}", f"Tax: {m(tax)}", f"Amount due: {m(total)}"]
    else:
        lines = [f"Bill To: {customer}", f"{rng.randint(2, 480)} {rng.choice(STREETS)}", "",
                 f"Remit to: {vendor}", addr, "", f"Invoice number {num}", f"Date of issue {fmt_date(issued, cur, rng)}",
                 due_line, "", *item_lines, "", f"Subtotal {m(sub)}", f"Tax {m(tax)}", f"Grand total {m(total)}"]
    gold = {"vendor": vendor, "invoice_number": num, "invoice_date": issued.isoformat(),
            "due_date": due.isoformat(), "total": f"{total:.2f}", "currency": cur}
    return "\n".join(lines) + "\n", gold


def main():
    rng = random.Random(409)
    for split, count in (("dev", 40), ("heldout", 40)):
        folder = ROOT / "data" / split
        folder.mkdir(parents=True, exist_ok=True)
        labels = {}
        for i in range(1, count + 1):
            text, gold = one(rng)
            doc = f"{split}-{i:03d}"
            (folder / f"{doc}.txt").write_text(text, encoding="utf-8")
            labels[doc] = gold
        (folder / "labels.json").write_text(json.dumps(labels, indent=1) + "\n", encoding="utf-8")
    print("wrote data/dev and data/heldout")


if __name__ == "__main__":
    main()
