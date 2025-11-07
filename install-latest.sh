#!/bin/bash
# Install or upgrade rpycbench to the latest version from GitHub releases

set -e

REPO="patrickkidd/rpycbench"

echo "Fetching latest release from GitHub..."

# Get latest release info from GitHub API
LATEST_URL=$(curl -s "https://api.github.com/repos/${REPO}/releases/latest" \
    | grep "browser_download_url.*\.whl" \
    | cut -d '"' -f 4)

if [ -z "$LATEST_URL" ]; then
    echo "Error: Could not find latest wheel in releases"
    exit 1
fi

echo "Found: $LATEST_URL"
echo "Installing..."

pip install --upgrade --force-reinstall "$LATEST_URL"

echo "✓ Successfully installed/upgraded rpycbench"
