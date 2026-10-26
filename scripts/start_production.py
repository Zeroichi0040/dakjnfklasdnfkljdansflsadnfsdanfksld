"""Apply migrations once, then replace this process with the production server."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
os.environ.setdefault("APP_ENV", "production")
subprocess.run([sys.executable, "manage.py", "db", "upgrade"], check=True)
os.execvp("gunicorn", ["gunicorn", "--config", "deploy/gunicorn.conf.py", "wsgi:app"])
