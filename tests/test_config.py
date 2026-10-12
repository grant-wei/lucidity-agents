"""The .env lookup order the course requires: the repo folder, then the folder above."""
from lucidity import config


def test_env_one_level_up_is_found(tmp_path, monkeypatch):
    repo = tmp_path / "lucidity-agents"
    repo.mkdir()
    (tmp_path / ".env").write_text("LUCIDITY_TEST_MARKER=above\n", encoding="utf-8")
    monkeypatch.setattr(config, "ROOT", repo)
    monkeypatch.delenv("LUCIDITY_TEST_MARKER", raising=False)
    assert config._load_env() == tmp_path / ".env"
    import os
    assert os.environ["LUCIDITY_TEST_MARKER"] == "above"
    monkeypatch.delenv("LUCIDITY_TEST_MARKER")


def test_repo_env_wins_over_the_one_above(tmp_path, monkeypatch):
    repo = tmp_path / "lucidity-agents"
    repo.mkdir()
    (tmp_path / ".env").write_text("X=1\n", encoding="utf-8")
    (repo / ".env").write_text("X=2\n", encoding="utf-8")
    monkeypatch.setattr(config, "ROOT", repo)
    assert config._load_env() == repo / ".env"


def test_env_example_has_placeholders_only():
    text = (config.ROOT / ".env.example").read_text(encoding="utf-8")
    for line in text.splitlines():
        if "=" in line and not line.startswith("#"):
            value = line.split("=", 1)[1]
            assert not value.startswith("sk-"), line
