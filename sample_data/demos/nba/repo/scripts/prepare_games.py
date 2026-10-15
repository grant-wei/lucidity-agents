"""Turn FiveThirtyEight's nbaallelo.csv (CC BY 4.0) into hoopkit/data/games.csv: one row per game, home team first."""
import csv
import sys
from datetime import datetime
from pathlib import Path

src, dest = Path(sys.argv[1]), Path(sys.argv[2])
rows = []
elo = []
with open(src, newline="", encoding="utf-8") as fh:
    for r in csv.DictReader(fh):
        if r["game_location"] != "H" or int(r["year_id"]) < 2001:
            continue
        d = datetime.strptime(r["date_game"], "%m/%d/%Y").date().isoformat()
        rows.append({"game_id": r["game_id"], "date": d, "season": int(r["year_id"]), "playoffs": int(r["is_playoffs"]),
                     "home": r["team_id"], "away": r["opp_id"], "home_pts": int(r["pts"]), "away_pts": int(r["opp_pts"])})
        elo.append((d, int(r["year_id"]), float(r["forecast"]), int(r["pts"]) > int(r["opp_pts"])))
rows.sort(key=lambda r: (r["date"], r["game_id"]))
dest.parent.mkdir(parents=True, exist_ok=True)
with open(dest, "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
import math
for name, seasons in [("dev", {2013}), ("heldout", {2014, 2015})]:
    e = [(p, y) for d, s, p, y in elo if s in seasons]
    ll = -sum(math.log(p if y else 1 - p) for p, y in e) / len(e)
    acc = sum((p > .5) == y for p, y in e) / len(e)
    print(name, len(e), "538 Elo log loss", round(ll, 4), "accuracy", round(acc, 4))
print(len(rows), "games", rows[0]["date"], rows[-1]["date"])
