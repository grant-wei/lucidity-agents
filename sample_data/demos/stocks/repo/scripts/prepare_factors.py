"""Turn Kenneth French's factor and industry files into data/factors.csv and data/industry_info.csv.

    python scripts/prepare_factors.py F-F_Research_Data_5_Factors_2x3.csv F-F_Momentum_Factor.csv \
        49_Industry_Portfolios.csv data/

factors.csv: one row per month from January 1970. The five Fama-French factors (market minus
T-bill, small minus big, value minus growth, robust minus weak profitability, conservative minus
aggressive investment), momentum (winners minus losers), and the T-bill rate. Monthly, in percent.
The same number for every industry: they describe the month, not the industry.

industry_info.csv: one row per industry per month from January 1970. firms is how many companies
are in the industry and size their average market value ($ millions), both measured at the end of
the month before. be_me is book equity over market value (high = cheap), from the industry file's
annual "Sum of BE / Sum of ME": the row for year Y uses fiscal-year Y-1 book equity and December Y-1
prices, and Fama and French treat it as known by the end of June Y. So it's filled in from July Y
to June Y+1.
"""
import csv
import sys
from pathlib import Path

ff5, mom, ind, out = (Path(a) for a in sys.argv[1:5])


def lines(p):
    return p.read_text(encoding="utf-8", errors="replace").splitlines()


def table(ls, title, key_len):
    """{key: {column: value}} for the block under `title`, keys being YYYYMM or YYYY."""
    i = next(k for k, ln in enumerate(ls) if title in ln) if title else 0
    while not ls[i].lstrip().startswith(","):
        i += 1
    names = [h.strip() for h in ls[i].split(",")[1:]]
    rows = {}
    for ln in ls[i + 1:]:
        cells = [c.strip() for c in ln.split(",")]
        if len(cells) < 2 or not (cells[0].isdigit() and len(cells[0]) == key_len):
            break
        rows[cells[0]] = {n: float(v) for n, v in zip(names, cells[1:]) if float(v) > -99}
    return names, rows


def month(k):
    return f"{k[:4]}-{k[4:]}"


_, f5 = table(lines(ff5), "", 6)
_, fm = table(lines(mom), "", 6)
il = lines(ind)
names, firms = table(il, "Number of Firms in Portfolios", 6)
_, size = table(il, "Average Firm Size", 6)
_, beme = table(il, "Sum of BE / Sum of ME", 4)
out.mkdir(parents=True, exist_ok=True)

cols = [("mkt_rf", "Mkt-RF"), ("smb", "SMB"), ("hml", "HML"), ("rmw", "RMW"), ("cma", "CMA"), ("mom", "Mom"), ("rf", "RF")]
frows = []
for k in sorted(f5):
    if month(k) >= "1970-01" and k in fm:
        both = {**f5[k], **fm[k]}
        frows.append({"month": month(k), **{c: f"{both[s]:.2f}" for c, s in cols}})
with open(out / "factors.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["month"] + [c for c, _ in cols])
    w.writeheader()
    w.writerows(frows)

irows = []
for k in sorted(size):
    m = month(k)
    if m < "1970-01":
        continue
    year = int(k[:4]) if int(k[4:]) >= 7 else int(k[:4]) - 1   # July Y to June Y+1 uses year Y's BE/ME
    for n in names:
        if n in size[k] and firms[k].get(n, 0) > 0:
            b = beme.get(str(year), {}).get(n)
            irows.append({"month": m, "industry": n, "firms": int(firms[k][n]), "size": f"{size[k][n]:.2f}",
                          "be_me": "" if b is None else f"{b:.2f}"})
with open(out / "industry_info.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=["month", "industry", "firms", "size", "be_me"])
    w.writeheader()
    w.writerows(irows)
print(len(frows), "factor months", frows[0]["month"], frows[-1]["month"], "|", len(irows), "industry rows")
