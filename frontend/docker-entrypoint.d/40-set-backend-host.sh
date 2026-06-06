#!/bin/sh
set -eu

if [ -z "${BACKEND_HOST:-}" ] && [ -n "${BACKEND_URL:-}" ]; then
  BACKEND_HOST=$(printf '%s' "$BACKEND_URL" | sed -E 's#^https?://([^/:]+).*#\1#')
  export BACKEND_HOST
fi
