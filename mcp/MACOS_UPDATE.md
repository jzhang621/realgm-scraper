# NIL PRO — Update Guide (Mac)

Follow these steps to get the latest version of the NIL PRO tools.

---

## Step 1 — Run the Update Command

1. Open **Terminal** — press `Cmd + Space`, type "Terminal", press Enter
2. Copy and paste the following command, then press Enter:
   ```
   bash <(curl -fsSL https://raw.githubusercontent.com/jzhang621/realgm-scraper/main/mcp/install_mac.sh)
   ```
3. You should see output like this:
   ```
   === NIL PRO MCP Installer (Mac) ===

   ✓ Python 3.12.x found
   Installing nil-pro-mcp...
   ✓ Installed at: /usr/local/bin/nil-pro-mcp
   ✓ Claude Desktop config updated: /Users/yourname/Library/Application Support/Claude/claude_desktop_config.json

   === Done! ===
   Restart Claude Desktop to activate the NIL PRO tools.
   ```

---

## Step 2 — Restart Claude Desktop

1. Fully quit Claude Desktop — click **Claude** in the menu bar at the top of your screen, then click **Quit Claude**
2. Reopen Claude Desktop from your Applications folder (or press `Cmd + Space`, type "Claude", press Enter)

---

## Step 3 — Verify It's Working

Start a new conversation in Claude Desktop and type:

```
Where does Ben Roseborough rank among all freshmen by NIL PRO rating in 2025-26?
```

**What you should see:**
- Claude calls the NIL PRO tools (you'll see "Used nil-pro integration" above the response)
- The response includes a rank like **#234 out of 1,169 freshmen** with `✅ EXHAUSTIVE COHORT RANK` confirming the full dataset was used

---

## Troubleshooting

**The install script output looks the same but Claude still gives old results**
Make sure you fully quit Claude Desktop (not just closed the window) — click Claude in the menu bar → Quit Claude — then reopen.

**"No players found" or timeout errors**
The backend may be starting up after inactivity. Wait 30 seconds and try again.

**The script fails or shows an error**
Take a screenshot of the Terminal output and send it over.
