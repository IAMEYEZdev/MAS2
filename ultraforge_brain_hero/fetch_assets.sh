#!/usr/bin/env bash
# Downloads the Higgsfield-generated UF brain assets into ./assets/.
# Run this from a machine with normal internet access (the Claude Code
# cloud sandbox that produced this package could not reach the CDN).
set -euo pipefail
cd "$(dirname "$0")"

BRAIN_PNG_URL="https://d8j0ntlcm91z4.cloudfront.net/user_3Ey8eJ36Q3HGBhZyKbl6svDZIQU/hf_20260612_235845_25fc4a87-36d3-497d-9f4f-ea6cf5fa812b.png"

mkdir -p assets

echo "Fetching UF brain still (Higgsfield job 25fc4a87, 2752x1536)..."
curl -fSL -o assets/uf-brain.png "$BRAIN_PNG_URL"
file assets/uf-brain.png || true

# When a Higgsfield video render exists (requires basic plan or higher),
# add its URL here and uncomment:
# BRAIN_MP4_URL=""
# curl -fSL -o assets/uf-brain-loop.mp4 "$BRAIN_MP4_URL"

echo "Done. Assets are in $(pwd)/assets/"
