"""Copy this into the PythonAnywhere WSGI editor and replace YOUR_USERNAME."""

import os
import sys
from pathlib import Path

project = Path("/home/YOUR_USERNAME/Flask_Fullstack_Framework")
sys.path.insert(0, str(project))
os.environ["APP_ENV"] = "production"
# wsgi.py reads the private project .env without replacing host-set variables.
from wsgi import app as application  # noqa: E402,F401
