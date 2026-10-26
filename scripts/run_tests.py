"""Run isolated tests. Installs the optional test tools if they are missing."""

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if importlib.util.find_spec("pytest") is None:
    print("Installing the optional development tools (internet needed this time)...")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", str(ROOT / "requirements-dev.txt")],
        check=True,
        cwd=ROOT,
    )
raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", *sys.argv[1:]], cwd=ROOT))
