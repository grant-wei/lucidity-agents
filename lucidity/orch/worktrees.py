"""Git plumbing for runs. Your checkout is never touched: a run gets its own integration branch
`lucidity/<run>` checked out in a worktree under state/, every task branches off it into a
worktree of its own, and only work the checker passed is merged back into the integration branch.
When the run is over you merge (or delete) that one branch yourself."""
import os
import shutil
import subprocess
from pathlib import Path

_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_ID = ["-c", "user.name=lucidity", "-c", "user.email=lucidity@localhost", "-c", "commit.gpgsign=false"]

# build caches and logs are never committed, whether or not the repo ignores them
JUNK = (":(glob)**/__pycache__/**", ":(glob)**/*.pyc", ":(glob)**/.pytest_cache/**", ":(glob)**/node_modules/**",
        ":(glob)**/.mypy_cache/**", ":(glob)**/.ruff_cache/**", ":(glob)**/*.log", ":(glob)**/.DS_Store")


class GitError(RuntimeError):
    pass


def git(cwd, *args, timeout=120, check=False):
    try:
        r = subprocess.run(["git", *args], cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout, creationflags=_FLAGS)
    except FileNotFoundError as e:
        raise GitError("git is not installed or not on PATH") from e
    if check and r.returncode != 0:
        raise GitError((r.stderr or r.stdout).strip()[-400:] or f"git {' '.join(args)} failed")
    return r


def available():
    return shutil.which("git") is not None


def is_repo(path):
    try:
        return git(path, "rev-parse", "--is-inside-work-tree").stdout.strip() == "true"
    except (GitError, OSError, subprocess.TimeoutExpired):
        return False


def toplevel(path):
    return Path(git(path, "rev-parse", "--show-toplevel", check=True).stdout.strip())


def head(path):
    return git(path, "rev-parse", "HEAD", check=True).stdout.strip()


def has_commits(path):
    return git(path, "rev-parse", "--verify", "--quiet", "HEAD").returncode == 0


def init_repo(path, message="initial commit"):
    """Turn a plain folder into a repo with one commit (used for the demo's toy repo)."""
    git(path, "init", "-q", "-b", "main", check=True)
    git(path, "add", "-A", check=True)
    git(path, *_ID, "commit", "-qm", message, check=True)
    return head(path)


def add(repo, path, branch, base):
    """New worktree at `path` on a new `branch` cut from `base`."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    git(repo, "worktree", "add", "-q", "-b", branch, str(path), base, check=True)
    return str(path)


def commit_all(path, message):
    """Commit everything in the worktree; the sha, or None when nothing but junk changed."""
    git(path, "add", "-A", check=True)
    git(path, "reset", "-q", "--", *JUNK)
    if git(path, "diff", "--cached", "--quiet").returncode == 0:
        return None
    git(path, *_ID, "commit", "-qm", message, check=True)
    return head(path)


def changed_files(path, base):
    """Files changed since `base`, committed or not."""
    out = set(git(path, "diff", "--name-only", base).stdout.split("\n"))
    for ln in git(path, "status", "--porcelain", "-uall").stdout.splitlines():
        if ln.strip():
            out.add(ln[3:].strip().strip('"'))
    return sorted(p.replace("\\", "/") for p in out
                  if p and not any(j in p for j in ("__pycache__", ".pytest_cache", ".pyc")))


def diff(path, base, limit=40_000):
    """Stat plus the diff since `base`, with new files included, for the checker to read."""
    git(path, "add", "-A", "-N")  # intent-to-add, so untracked files show up in the diff
    skip = ("--", ".") + tuple(j.replace(":(glob)", ":(exclude,glob)") for j in JUNK)
    stat = git(path, "diff", "--stat", base, *skip).stdout.strip()
    body = git(path, "diff", base, *skip).stdout
    if len(body) > limit:
        body = body[:limit] + f"\n... (diff cut at {limit} characters)"
    return f"{stat}\n\n{body}".strip() or "(no changes)"


def merge(path, branch, message):
    """Merge `branch` into whatever is checked out at `path` with --no-ff.
    {"ok", "conflicts", "error", "commit"}; a conflicted merge is aborted, leaving `path` clean."""
    r = git(path, *_ID, "merge", "--no-ff", "-m", message, branch, timeout=300)
    if r.returncode == 0:
        return {"ok": True, "conflicts": [], "error": None, "commit": head(path)}
    conflicts = [ln[3:] for ln in git(path, "status", "--porcelain").stdout.splitlines()
                 if ln[:2] in ("UU", "AA", "DU", "UD", "AU", "UA", "DD")]
    git(path, "merge", "--abort")
    return {"ok": False, "conflicts": conflicts, "error": (r.stderr or r.stdout).strip()[-400:], "commit": None}


def remove(repo, path, branch=None):
    if path and os.path.isdir(path):
        git(repo, "worktree", "remove", "--force", str(path))
    git(repo, "worktree", "prune")
    if branch:
        git(repo, "branch", "-D", branch)
