#!/usr/bin/env python3
"""Install or upgrade rpycbench to the latest version from GitHub releases"""

import sys
import json
import subprocess
import urllib.request

REPO = "patrickkidd/rpycbench"

def get_latest_wheel_url():
    """Fetch the latest wheel URL from GitHub API"""
    api_url = f"https://api.github.com/repos/{REPO}/releases/latest"

    try:
        with urllib.request.urlopen(api_url) as response:
            data = json.loads(response.read())

        # Find wheel asset
        for asset in data.get('assets', []):
            if asset['name'].endswith('.whl'):
                return asset['browser_download_url']

        return None
    except Exception as e:
        print(f"Error fetching release info: {e}", file=sys.stderr)
        return None

def main():
    print("Fetching latest release from GitHub...")

    wheel_url = get_latest_wheel_url()

    if not wheel_url:
        print("Error: Could not find latest wheel in releases", file=sys.stderr)
        return 1

    print(f"Found: {wheel_url}")
    print("Installing...")

    # Install with pip
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", "--force-reinstall", wheel_url],
        capture_output=False
    )

    if result.returncode == 0:
        print("\n✓ Successfully installed/upgraded rpycbench")
    else:
        print("\n✗ Installation failed", file=sys.stderr)

    return result.returncode

if __name__ == '__main__':
    sys.exit(main())
