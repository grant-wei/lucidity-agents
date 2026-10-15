"""Bring a CSV: any table becomes a repo with a fixed split, a starting model, a locked scorer and a test."""
import csv
import json
import os
import random
import subprocess
import sys
from pathlib import Path

import pytest

from lucidity.orch import csvrepo, runs

ROOT = Path(__file__).resolve().parent.parent


def _write(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)
    return path


def _score(repo, *args, role=None):
    env = {**os.environ, **({"LUCIDITY_ROLE": role} if role else {})}
    return subprocess.run([sys.executable, "evals/score.py", *args], cwd=repo, capture_output=True, text=True, env=env)


def test_bundled_example_builds_and_locks_the_test_split(tmp_path):
    a = csvrepo.build("examples/breast_cancer.csv", "diagnosis", tmp_path)
    repo = Path(a["repo"])
    assert a["kind"] == "binary" and a["metric"] == "log_loss"
    assert "0.6931" in json.dumps(a["references"]) and a["start_test"] < 0.6931
    assert "or lower" in a["goal"] and "dev split" in a["goal"]
    refused = _score(repo, role="agent")
    assert refused.returncode == 2 and "referee" in refused.stdout
    dev = json.loads(_score(repo, "--split", "dev", role="agent").stdout)
    assert set(dev["metrics"]) == {"log_loss", "accuracy", "auc"}
    tests = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=repo, capture_output=True, text=True)
    assert tests.returncode == 0, tests.stdout
    assert csvrepo.build("examples/breast_cancer.csv", "diagnosis", tmp_path) == a   # same table, same repo


def test_split_is_fixed_and_roughly_60_20_20():
    s = [csvrepo.split_of_row(i) for i in range(1, 5001)]
    assert s == [csvrepo.split_of_row(i) for i in range(1, 5001)]
    assert 0.17 < s.count("heldout") / len(s) < 0.23 and 0.17 < s.count("dev") / len(s) < 0.23


def test_regression_and_multiclass_tables(tmp_path):
    rnd = random.Random(0)
    rows = [[round(x := rnd.uniform(0, 10), 3), round(z := rnd.uniform(0, 1), 3), rnd.choice("abc"),
             round(3 * x + 2 * z + rnd.gauss(0, 1), 3)] for _ in range(300)]
    a = csvrepo.build(_write(tmp_path / "house.csv", ["size", "age", "zone", "price"], rows), None, tmp_path / "r")
    assert a["kind"] == "regression" and a["metric"] == "rmse" and a["target"] == "price"
    assert set(json.loads(_score(Path(a["repo"]), "--split", "dev").stdout)["metrics"]) == {"rmse", "r2"}
    rows = [[rnd.uniform(0, 1), rnd.choice(["red", "green", "blue"])] for _ in range(200)]
    a = csvrepo.build(_write(tmp_path / "colors.csv", ["x", "color"], rows), "color", tmp_path / "m")
    assert a["kind"] == "multiclass" and a["metric"] == "log_loss"
    assert "accuracy" in json.loads(_score(Path(a["repo"])).stdout)["metrics"]


def test_bad_tables_say_why(tmp_path):
    with pytest.raises(csvrepo.CsvError, match="no file"):
        csvrepo.build(tmp_path / "missing.csv")
    with pytest.raises(csvrepo.CsvError, match="at least 50"):
        csvrepo.build(_write(tmp_path / "tiny.csv", ["x", "y"], [[1, 0], [2, 1]]))
    with pytest.raises(csvrepo.CsvError, match="no column named"):
        csvrepo.build("examples/breast_cancer.csv", "nope", tmp_path)


def test_run_page_reads_the_repos_about_json(tmp_path):
    a = csvrepo.build("examples/breast_cancer.csv", "diagnosis", tmp_path)
    about = runs._about(a["repo"])
    assert about["split"] == a["split"] and about["references"] == a["references"]
    assert runs._about(tmp_path) == {}


def test_time_split_tests_on_the_newest_rows(tmp_path):
    rnd = random.Random(1)
    rows = [[f"{2000 + i // 40}-{1 + i % 12:02d}-15", i + 1000, round(rnd.uniform(0, 1), 3), rnd.choice("yn")]
            for i in range(400)]
    path = _write(tmp_path / "sales.csv", ["date", "order_no", "x", "bought"], rows)
    cols = csvrepo.columns(path)
    assert cols["dates"] == ["date"] and cols["ids"] == ["order_no"]
    a = csvrepo.build(path, "bought", tmp_path / "t", split_by="date")
    assert a["split"].startswith("Rows are split by date: trained on 2000-01-15") and "tested on 2008" in a["split"]
    with open(Path(a["repo"]) / "data" / "rows.csv", encoding="utf-8") as fh:
        got = list(csv.DictReader(fh))
    newest_train = max(r["date"] for r in got if r["_split"] == "train")
    assert all(r["date"] > newest_train for r in got if r["_split"] == "heldout")
    features = (Path(a["repo"]) / "tablemodel" / "features.py").read_text(encoding="utf-8")
    assert "order_no" not in features.split("NAMES =")[1]   # an ID is never a starting input
    assert json.loads(_score(Path(a["repo"]), "--split", "dev").stdout)["rows"] > 0


def test_group_split_keeps_each_group_together(tmp_path):
    rnd = random.Random(2)
    rows = [[f"c{i % 60}", round(rnd.uniform(0, 1), 3), rnd.choice("yn")] for i in range(600)]
    path = _write(tmp_path / "visits.csv", ["customer", "x", "churn"], rows)
    assert csvrepo.columns(path)["groups"] == ["customer"]   # x is a measurement, not something to group by
    a = csvrepo.build(path, "churn", tmp_path / "g", group_by="customer")
    with open(Path(a["repo"]) / "data" / "rows.csv", encoding="utf-8") as fh:
        got = list(csv.DictReader(fh))
    sides = {}
    for r in got:
        sides.setdefault(r["customer"], set()).add(r["_split"])
    assert all(len(s) == 1 for s in sides.values()) and "same customer always land together" in a["split"]
    with pytest.raises(csvrepo.CsvError, match="not both"):
        csvrepo.build(tmp_path / "visits.csv", "churn", tmp_path / "g2", split_by="customer", group_by="customer")


def test_about_says_how_the_goal_was_set(tmp_path):
    a = csvrepo.build("examples/breast_cancer.csv", "diagnosis", tmp_path)
    assert a["goal_value"] == round(a["start_test"] * 0.9, 3)
    assert f"to {a['goal_value']} or lower" in a["goal"]
    assert a["start_model"] == "LogisticRegression" and len(a["start_columns"]) == 2
    assert "10%" in a["goal_rule"] and a["lower_is_better"]


def test_benchmark_is_plain_regression_on_every_column(tmp_path):
    a = csvrepo.build("examples/diabetes.csv", None, tmp_path)
    b = a["benchmark"]
    assert b["model"] == "LinearRegression" and b["penalty"] == "none" and b["columns"] == a["numeric_columns"]
    assert b["value"] < a["start_test"]   # all ten columns beat the two-column start
    assert [r for r in a["references"] if r.get("benchmark")] == [{"label": b["label"], "value": b["value"], "benchmark": True}]


def test_upload_is_saved_once_and_readable(tmp_path, monkeypatch):
    monkeypatch.setattr(csvrepo.config, "STATE_DIR", tmp_path)
    data = Path("examples/diabetes.csv").read_bytes()
    a, b = csvrepo.save_upload("My Table.csv", data), csvrepo.save_upload("My Table.csv", data)
    assert a == b and Path(a).parent == tmp_path / "uploads" and Path(a).read_bytes() == data
    assert csvrepo.columns(a)["rows"] > 100
    with pytest.raises(csvrepo.CsvError):
        csvrepo.save_upload("empty.csv", b"")
