"""The .env lookup order the course requires: the repo folder, then the folder above."""
import os

from lucidity import config


def make_repo(tmp_path, monkeypatch):
    repo = tmp_path / "lucidity-agents"
    repo.mkdir()
    monkeypatch.setattr(config, "ROOT", repo)
    monkeypatch.setenv("OPENAI_API_KEY", "already-set")      # so a test key never leaks into other tests
    return repo


def test_env_one_level_up_is_found(tmp_path, monkeypatch):
    make_repo(tmp_path, monkeypatch)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-test-above\nLUCIDITY_TEST_MARKER=above\n", encoding="utf-8")
    monkeypatch.delenv("LUCIDITY_TEST_MARKER", raising=False)
    assert config._load_env() == tmp_path / ".env"
    assert os.environ["LUCIDITY_TEST_MARKER"] == "above"
    monkeypatch.delenv("LUCIDITY_TEST_MARKER")


def test_repo_env_wins_over_the_one_above(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, monkeypatch)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-test-above\n", encoding="utf-8")
    (repo / ".env").write_text("OPENAI_API_KEY=sk-test-repo\n", encoding="utf-8")
    assert config._load_env() == repo / ".env"


def test_a_copied_example_env_does_not_hide_the_real_one_above(tmp_path, monkeypatch):
    # what a grader gets by following step 2 with the staff .env already one folder up
    repo = make_repo(tmp_path, monkeypatch)
    (tmp_path / ".env").write_text("OPENAI_API_KEY=sk-test-above\n", encoding="utf-8")
    (repo / ".env").write_text(EXAMPLE, encoding="utf-8")
    assert config._load_env() == tmp_path / ".env"


def test_no_real_key_anywhere(tmp_path, monkeypatch):
    repo = make_repo(tmp_path, monkeypatch)
    (repo / ".env").write_text(EXAMPLE, encoding="utf-8")
    assert config._load_env() is None


def test_placeholder_key_is_not_a_key(monkeypatch):
    for value, ok in [(config.PLACEHOLDER_KEY, False), ("", False), ("sk-test", True)]:
        monkeypatch.setenv("OPENAI_API_KEY", value)
        assert config.has_key() is ok


EXAMPLE = (config.ROOT / ".env.example").read_text(encoding="utf-8")


def test_env_example_has_placeholders_only():
    for line in EXAMPLE.splitlines():
        if "=" in line and not line.startswith("#"):
            value = line.split("=", 1)[1]
            assert not value.startswith("sk-"), line
