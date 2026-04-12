#!/bin/bash
# Build dashboard and copy static files into the Python package
set -e
cd "$(dirname "$0")/../dashboard"
rm -rf out .next
npx next build
rm -rf ../engramkit/dashboard_static
cp -r out ../engramkit/dashboard_static
echo "Dashboard built and copied to engramkit/dashboard_static/"
