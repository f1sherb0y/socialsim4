#!/usr/bin/env bash
set -euo pipefail

python -m socialsim4.backend.scripts.ensure_admin

# If a backend root path is provided (e.g. /css/socialsim), pass it to uvicorn
EXTRA_ARGS=()
if [[ -n "${SOCIALSIM4_BACKEND_ROOT_PATH:-}" ]]; then
  EXTRA_ARGS+=(--root-path "${SOCIALSIM4_BACKEND_ROOT_PATH}")
fi

exec uvicorn socialsim4.backend.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --proxy-headers \
  --forwarded-allow-ips='*' \
  "${EXTRA_ARGS[@]}"
