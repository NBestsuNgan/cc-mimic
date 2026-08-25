#!/usr/bin/env bash
# Build the image on your laptop and push it to a registry. Run this, not the VM.
#     IMAGE=ghcr.io/<you>/cc-mimic:latest bash deploy/build-push.sh
set -euo pipefail
: "${IMAGE:?set IMAGE, e.g. IMAGE=ghcr.io/you/cc-mimic:latest}"
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Must match the VM's CPU: linux/arm64 for Oracle Ampere A1, linux/amd64 for Oracle's
# AMD E2.1.Micro or a GCP e2-micro. Override per-build:  PLATFORM=linux/amd64 bash ...
# Apple Silicon builds arm64 natively and cross-builds amd64 via buildx.
PLATFORM="${PLATFORM:-linux/arm64}"

echo "building for $PLATFORM"
docker buildx build --platform "$PLATFORM" -t "$IMAGE" --push .

echo
echo "pushed $IMAGE"
echo "on the VM: sudo bash deploy/update.sh"
