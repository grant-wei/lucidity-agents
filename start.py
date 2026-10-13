"""One command from a fresh clone: `python start.py`.

Makes .venv if it's missing, installs requirements.txt into it when that file changes, then runs
app.py with the venv's Python. Standard library only, so it works before anything is installed.
Extra arguments are ignored; settings come from environment variables and .env (see README)."""
import hashlib
import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PY = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
STAMP = VENV / ".requirements.sha1"


def main():
    if sys.version_info < (3, 10):
        sys.exit(f"Lucidity needs Python 3.10 or newer; this is {sys.version.split()[0]}.")
    if not PY.exists():
        print("Making a virtual environment in .venv ...", flush=True)
        venv.EnvBuilder(with_pip=True).create(VENV)
    want = hashlib.sha1((ROOT / "requirements.txt").read_bytes()).hexdigest()
    if not STAMP.exists() or STAMP.read_text().strip() != want:
        print("Installing requirements (first run only, about a minute) ...", flush=True)
        subprocess.check_call([str(PY), "-m", "pip", "install", "-q", "--disable-pip-version-check",
                               "-r", str(ROOT / "requirements.txt")])
        STAMP.write_text(want)
    print("Starting Lucidity. Ctrl+C to stop.", flush=True)
    try:
        sys.exit(subprocess.call([str(PY), str(ROOT / "app.py")], cwd=ROOT))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
