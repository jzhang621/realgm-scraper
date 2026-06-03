#!/bin/bash
# NIL PRO MCP — Mac Installer
# Usage: bash install_mac.sh

set -e

echo "=== NIL PRO MCP Installer (Mac) ==="
echo ""

# 1. Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 is not installed."
    echo "Download it from https://www.python.org/downloads/ then re-run this script."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(sys.version_info.minor)')
if [ "$PYTHON_VERSION" -lt 10 ]; then
    echo "ERROR: Python 3.10 or higher is required (you have 3.$PYTHON_VERSION)."
    echo "Download a newer version from https://www.python.org/downloads/"
    exit 1
fi

echo "✓ Python 3.$PYTHON_VERSION found"

# 2. Install the package
echo ""
echo "Installing nil-pro-mcp..."
pip3 install --quiet --force-reinstall "git+https://github.com/jzhang621/realgm-scraper.git#subdirectory=mcp"

# 3. Find the installed command path
CMD=$(which nil-pro-mcp 2>/dev/null || python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))" | xargs -I{} echo "{}/nil-pro-mcp")

if [ ! -f "$CMD" ]; then
    echo "ERROR: nil-pro-mcp was installed but could not be located."
    echo "Try running: pip3 show nil-pro-mcp"
    exit 1
fi

echo "✓ Installed at: $CMD"

# 4. Update Claude Desktop config
CONFIG_DIR="$HOME/Library/Application Support/Claude"
CONFIG_FILE="$CONFIG_DIR/claude_desktop_config.json"

mkdir -p "$CONFIG_DIR"

python3 - "$CONFIG_FILE" "$CMD" <<'PYEOF'
import json, sys, os

config_file = sys.argv[1]
cmd_path    = sys.argv[2]

if os.path.exists(config_file):
    with open(config_file) as f:
        config = json.load(f)
else:
    config = {}

config.setdefault("mcpServers", {})["nil-pro"] = {
    "command": cmd_path,
    "env": {
        "NIL_PRO_API_URL": "https://realgm-scraper.onrender.com"
    }
}

with open(config_file, "w") as f:
    json.dump(config, f, indent=2)

print(f"✓ Claude Desktop config updated: {config_file}")
PYEOF

echo ""
echo "=== Done! ==="
echo "Restart Claude Desktop to activate the NIL PRO tools."
