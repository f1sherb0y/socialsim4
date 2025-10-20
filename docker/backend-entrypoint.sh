#!/usr/bin/env bash
set -euo pipefail

python -m socialsim4.backend.scripts.ensure_admin

exec uvicorn socialsim4.backend.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'
