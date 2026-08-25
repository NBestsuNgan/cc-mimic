#!/usr/bin/env bash
# Deploy a new image. Run deploy/build-push.sh on your laptop first.
# Secrets in /etc/cc-mimic are left untouched.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 1; }
cd /opt/cc-mimic
set -a; . /etc/cc-mimic/deploy.env; set +a
docker compose pull
docker compose up -d
docker image prune -f
