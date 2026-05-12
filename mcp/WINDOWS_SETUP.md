# NIL PRO — Windows Setup Guide

Follow these steps in order. Each section has a verification step so you know it worked before moving on.

---

## Step 1 — Install Claude Desktop

1. Open a browser and go to **https://claude.ai/download**
2. Click **"Download for Windows"**
3. Open the downloaded file (it will be named something like `Claude-Setup-x64.exe`)
4. Follow the installer prompts and click **Install**
5. When it finishes, Claude Desktop will open automatically

**Verify it works:**
- Claude Desktop opens and shows a chat window
- Sign in with your Anthropic account (or create one at claude.ai if you don't have one)
- You should be able to type a message and get a response

---

## Step 2 — Install Python

1. Open a browser and go to **https://www.python.org/downloads/**
2. Click the yellow **"Download Python 3.x.x"** button at the top (whichever version is shown — anything 3.10 or higher is fine)
3. Open the downloaded file (it will be named something like `python-3.12.x-amd64.exe`)
4. **IMPORTANT:** On the first screen of the installer, check the box that says **"Add Python to PATH"** before clicking anything else

   ![Check "Add Python to PATH" at the bottom of the installer screen]

5. Click **"Install Now"**
6. When it finishes, click **Close**

**Verify it works:**
1. Press the **Windows key**, type `cmd`, and press **Enter** — this opens the Command Prompt (a black window)
2. Type the following and press Enter:
   ```
   python --version
   ```
3. You should see something like:
   ```
   Python 3.12.3
   ```
4. Then type this and press Enter:
   ```
   pip --version
   ```
5. You should see something like:
   ```
   pip 24.0 from C:\Users\YourName\AppData\...
   ```

If either command says `not recognized`, Python was not added to PATH. Re-run the Python installer, choose **"Modify"**, and make sure **"Add Python to PATH"** is checked.

---

## Step 3 — Run the NIL PRO Installer

1. Download the installer file: **[install_windows.ps1](https://raw.githubusercontent.com/jzhang621/realgm-scraper/main/mcp/install_windows.ps1)**
   - Right-click that link and choose **"Save link as..."**
   - Save it somewhere easy to find, like your Desktop

2. Right-click the downloaded `install_windows.ps1` file and choose **"Run with PowerShell"**

3. If a blue window appears asking about execution policy, type `Y` and press Enter

4. The script will run and you should see:
   ```
   OK Python found: Python 3.12.x
   Installing nil-pro-mcp...
   OK Installed at: C:\Users\...
   OK Claude Desktop config updated: C:\Users\...
   === Done! ===
   Restart Claude Desktop to activate the NIL PRO tools.
   ```

5. Press Enter to close the window

**If the script is blocked by Windows Defender:**
- Click **"More info"** then **"Run anyway"**
- Or open PowerShell manually (Windows key → type "PowerShell" → Enter) and run:
  ```
  Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
  ```
  Then try double-clicking the script again.

---

## Step 4 — Restart Claude Desktop and Verify

1. Fully quit Claude Desktop — right-click the icon in the taskbar and choose **Quit**
2. Reopen Claude Desktop from the Start menu or desktop shortcut
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

**"nil-pro-mcp was installed but could not be located"**
Open Command Prompt and run:
```
pip show nil-pro-mcp
```
Look for the `Location:` line, then navigate one folder up to `Scripts\` — that's where `nil-pro-mcp.exe` lives. Copy that full path and manually add it to the Claude Desktop config file at:
```
C:\Users\YourName\AppData\Roaming\Claude\claude_desktop_config.json
```

**Claude Desktop doesn't show the tools**
Make sure you fully quit and restarted Claude Desktop (not just closed the window). Check the config file exists at `C:\Users\YourName\AppData\Roaming\Claude\claude_desktop_config.json` and contains a `nil-pro` entry under `mcpServers`.

**"No players found" responses**
The backend may be starting up (it sleeps after inactivity). Wait 30 seconds and try again.
