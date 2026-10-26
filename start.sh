#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
if [ ! -f .venv/bin/python ]; then
  echo 'Run bash setup.sh first.'
  exit 1
fi
exec .venv/bin/python run.py "$@"
