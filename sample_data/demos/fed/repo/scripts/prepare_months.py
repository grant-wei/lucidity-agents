"""Turn FRED downloads into data/months.csv, one row per month from 1985.

    python scripts/prepare_months.py <folder of FRED csvs> data/months.csv

Needs DFEDTAR (target rate to 2008-12-15), DFEDTARU (upper bound of the target range after),
DGS3MO, DGS2, DGS10 (daily Treasury yields), UNRATE and CPIAUCNS (monthly). Rates and yields are
the last value of each month. Unemployment and inflation are the previous month's, since a month's
figures come out early the next month. CPIAUCNS is not seasonally adjusted, so it is never revised.
hike_next is 1 when the target at the end of next month is above the target at the end of this one.
"""
import csv
import sys
from pathlib import Path

src, dest = Path(sys.argv[1]), Path(sys.argv[2])


def read(name):
    with open(src / f"{name}.csv", newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))[1:]
    return [(d, float(v)) for d, v in rows if v not in ("", ".")]


def month_end(series):
    out = {}
    for d, v in series:   # dates ascending, so the last value in a month wins
        out[d[:7]] = v
    return out


def shift(month, k):
    y, m = int(month[:4]), int(month[5:]) + k
    y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
    return f"{y:04d}-{m:02d}"


target = month_end(read("DFEDTAR") + read("DFEDTARU"))
y3m, y2, y10 = month_end(read("DGS3MO")), month_end(read("DGS2")), month_end(read("DGS10"))
def carried(series):
    """Monthly values, with a month that was never published (October 2025, the shutdown) carrying the last one."""
    out = {d[:7]: v for d, v in series}
    m = min(out)
    while m < max(out):
        m = shift(m, 1)
        out.setdefault(m, out[shift(m, -1)])
    return out


unrate, cpi = carried(read("UNRATE")), carried(read("CPIAUCNS"))


rows = []
months = sorted(m for m in target if m >= "1985-01")
for m in months:
    nxt, prev, prev13 = shift(m, 1), shift(m, -1), shift(m, -13)
    if nxt not in target or prev not in target or prev13 not in cpi or prev not in unrate:
        continue
    rows.append({
        "month": m, "target": target[m], "target_change": round(target[m] - target[prev], 4),
        "yield_3m": y3m[m], "yield_2y": y2[m], "yield_10y": y10[m],
        "unemployment": unrate[prev], "unemployment_change_3m": round(unrate[prev] - unrate[shift(m, -4)], 2),
        "inflation": round(100 * (cpi[prev] / cpi[prev13] - 1), 2),
        "hike_next": int(target[nxt] > target[m] + 1e-9),
    })
dest.parent.mkdir(parents=True, exist_ok=True)
with open(dest, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(len(rows), "months", rows[0]["month"], "to", rows[-1]["month"], sum(r["hike_next"] for r in rows), "hikes")
