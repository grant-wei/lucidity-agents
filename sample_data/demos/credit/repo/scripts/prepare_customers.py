"""Turn UCI's "default of credit card clients.xls" (CC BY 4.0) into data/customers.csv with readable columns.

Needs xlrd. Status columns: -2 no balance, -1 paid in full, 0 revolving, 1-9 months late.
"""
import csv
import sys
from pathlib import Path

import xlrd

MONTHS = ["sep", "aug", "jul", "jun", "may", "apr"]
COLS = (["id", "credit_limit", "sex", "education", "marriage", "age"] + [f"status_{m}" for m in MONTHS]
        + [f"bill_{m}" for m in MONTHS] + [f"paid_{m}" for m in MONTHS] + ["default"])
SEX = {1: "male", 2: "female"}
MARRIAGE = {1: "married", 2: "single", 3: "other", 0: "other"}

src, dest = Path(sys.argv[1]), Path(sys.argv[2])
sheet = xlrd.open_workbook(str(src)).sheet_by_index(0)
rows = []
for r in range(2, sheet.nrows):
    v = dict(zip(COLS, (int(x) for x in sheet.row_values(r))))
    v["sex"], v["marriage"] = SEX[v["sex"]], MARRIAGE[v["marriage"]]
    rows.append(v)
dest.parent.mkdir(parents=True, exist_ok=True)
with open(dest, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=COLS)
    w.writeheader()
    w.writerows(rows)
print(len(rows), "customers,", sum(r["default"] for r in rows), "defaults")
