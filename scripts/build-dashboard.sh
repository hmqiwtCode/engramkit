#!/bin/bash
# Build dashboard and copy static files into the Python package.
#
# The bundled dashboard is served by the Python API on the same origin, so
# the API base URL must NOT be hardcoded into the JS chunks. Force the env
# var to empty during the build to override any local `.env.local` a dev
# may have set for talking to a separate :8000 backend.
set -euo pipefail

cd "$(dirname "$0")/../dashboard"
rm -rf out .next
NEXT_PUBLIC_ENGRAMKIT_API_URL="" npx next build

TARGET="../engramkit/dashboard_static"
rm -rf "$TARGET"
cp -r out "$TARGET"

# Sanity check: ensure we didn't nest a stale `out/` subdirectory inside the
# package (which would bloat the wheel with a 1.3 MB duplicate tree).
if [ -d "$TARGET/out" ]; then
    echo "ERROR: $TARGET/out exists — duplicate tree detected" >&2
    exit 1
fi

echo "Dashboard built and copied to engramkit/dashboard_static/"
