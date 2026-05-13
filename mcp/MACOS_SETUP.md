# NIL PRO — Mac Setup Guide

Follow these steps in order. Each section has a verification step so you know it worked before moving on.

---

## Step 1 — Install Claude Desktop

1. Open a browser and go to **https://claude.ai/download**
2. Click **"Download for Mac"**
3. Open the downloaded `.dmg` file
4. Drag the **Claude** icon into your **Applications** folder
5. Open Claude from your Applications folder (or Spotlight: press `Cmd + Space`, type "Claude", press Enter)
6. Sign in with your Anthropic account (or create one at claude.ai if you don't have one)

**Verify it works:**
- Claude Desktop opens and shows a chat window
- You can type a message and get a response

---

## Step 2 — Install Python

Mac comes with Python pre-installed but it's often outdated. Follow these steps to get a current version.

1. Open a browser and go to **https://www.python.org/downloads/**
2. Click the yellow **"Download Python 3.x.x"** button (anything 3.10 or higher is fine)
3. Open the downloaded `.pkg` file
4. Follow the installer — click **Continue**, **Agree**, **Install**
5. Enter your Mac password if prompted

**Verify it works:**
1. Open **Terminal** — press `Cmd + Space`, type "Terminal", press Enter
2. Type the following and press Enter:
   ```
   python3 --version
   ```
3. You should see something like:
   ```
   Python 3.12.3
   ```
4. Then type this and press Enter:
   ```
   pip3 --version
   ```
5. You should see something like:
   ```
   pip 24.0 from /Library/Frameworks/Python.framework/...
   ```

If you see `command not found`, try closing Terminal and reopening it, then try again.

---

## Step 3 — Run the NIL PRO Installer

1. Open **Terminal** (press `Cmd + Space`, type "Terminal", press Enter)
2. Copy and paste the following command into Terminal, then press Enter:
   ```
   bash <(curl -fsSL https://raw.githubusercontent.com/jzhang621/realgm-scraper/main/mcp/install_mac.sh)
   ```
3. You may be prompted to enter your Mac password — this is normal
4. The script will run and you should see:
   ```
   ✓ Python 3.12.x found
   Installing nil-pro-mcp...
   ✓ Installed at: /usr/local/bin/nil-pro-mcp
   ✓ Claude Desktop config updated: /Users/yourname/Library/Application Support/Claude/claude_desktop_config.json

   === Done! ===
   Restart Claude Desktop to activate the NIL PRO tools.
   ```

---

## Step 4 — Restart Claude Desktop and Verify

1. Fully quit Claude Desktop — click **Claude** in the menu bar at the top of the screen, then click **Quit Claude**
2. Reopen Claude Desktop from your Applications folder
3. Start a new conversation and type:
   ```
   Search for Cooper Flagg in NIL PRO
   ```
4. Claude should use the NIL PRO tools automatically and return player results

**How to tell the tools are active:**
- You'll see a small tools/hammer icon near the chat input
- When Claude responds, you'll see a line like "Used nil-pro integration" above the answer

---

## Troubleshooting

**"command not found: python3" or "command not found: pip3"**
Close Terminal, reopen it, and try again. If still not working, re-run the Python installer from python.org and make sure it completes successfully.

**The install script says "nil-pro-mcp not found"**
Run this in Terminal:
```
pip3 show nil-pro-mcp
```
Look for the `Location:` line — the command lives one level up in a `bin/` folder next to it. Email that path and we can update the config manually.

**Claude Desktop doesn't show the tools after restarting**
Make sure you fully quit Claude (not just closed the window). Then reopen and try again.

**"No players found" responses**
The backend may be starting up after a period of inactivity. Wait 30 seconds and try the same question again.
