#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_demo
printf '%s\n' 'Open http://127.0.0.1:8000/ | Demo: demo / Demo12345!'
exec .venv/bin/python manage.py runserver 127.0.0.1:8000
