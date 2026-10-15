"""Turn Kenneth French's 49_Industry_Portfolios.csv into data/returns.csv: one row per industry per month.

Value-weighted monthly returns in percent, from January 1970. Months where an industry has no
portfolio (-99.99) are left out.
"""
import csv
import sys
from pathlib import Path

src, dest = Path(sys.argv[1]), Path(sys.argv[2])
lines = src.read_text(encoding="utf-8", errors="replace").splitlines()
start = next(i for i, ln in enumerate(lines) if "Average Value Weighted Returns -- Monthly" in ln) + 1
names = [h.strip() for h in lines[start].split(",")[1:]]
rows = []
for ln in lines[start + 1:]:
    cells = [c.strip() for c in ln.split(",")]
    if len(cells) < 2 or not cells[0].isdigit():
        break
    month = f"{cells[0][:4]}-{cells[0][4:]}"
    if month < "1970-01":
        continue
    for name, v in zip(names, cells[1:]):
        if float(v) > -99:
            rows.append({"month": month, "industry": name, "ret": v})
dest.parent.mkdir(parents=True, exist_ok=True)
with open(dest, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["month", "industry", "ret"])
    w.writeheader()
    w.writerows(rows)
print(len(rows), "rows", rows[0]["month"], rows[-1]["month"], len(names), "industries")
