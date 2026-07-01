# NIL PRO — Local Dev Setup (Mac)

This guide sets up the full NIL PRO stack locally: FastAPI backend (connected to Neon cloud PostgreSQL), MCP server, and Claude Code CLI.

Follow the steps in order. Each section has a verification step.

---

## Step 1 — Install Prerequisites

### Homebrew
Homebrew is a package manager for Mac. If you don't have it:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
Follow any prompts. When done, close and reopen Terminal.

**Verify:** `brew --version` → should print a version number.

### Python 3.10+
```bash
brew install python@3.12
```
**Verify:** `python3 --version` → `Python 3.12.x`

### Git
```bash
brew install git
```
**Verify:** `git --version`

---

## Step 2 — Install Claude Code CLI

```bash
npm install -g @anthropic-ai/claude-code
```

If you don't have Node/npm:
```bash
brew install node
npm install -g @anthropic-ai/claude-code
```

**Verify:** `claude --version`

Then log in:
```bash
claude
```
Follow the browser prompt to authenticate with your Anthropic account. Once authenticated, press `Ctrl+C` to exit.

---

## Step 3 — Clone the Repo

```bash
git clone https://github.com/jzhang621/realgm-scraper.git
cd realgm-scraper
```

---

## Step 4 — Set Up the Backend

### Install Python dependencies
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Create the .env file

You'll need the Neon connection string — get this from Jimmy before proceeding.

```bash
cat > .env << 'EOF'
DATABASE_URL=postgresql+psycopg2://...   # paste the Neon connection string here
AUTH_USERNAME=
AUTH_PASSWORD=
AUTH_SECRET=
EOF
```

### Run the backend server
```bash
uvicorn main:app --reload --port 8000
```

Leave this terminal window open — the server needs to stay running.

**Verify:** Open a new Terminal tab and run:
```bash
curl http://localhost:8000/api/players/2025-26?limit=1
```
You should get a JSON response with player data.

---

## Step 6 — Install the MCP Server from Source

Open a **new Terminal tab** (keep the backend running in the other tab).

```bash
cd /path/to/realgm-scraper/mcp   # adjust to where you cloned the repo
pip3 install -e .
```

**Verify:**
```bash
nil-pro-mcp --help
```
Should print the MCP server help output.

---

## Step 7 — Configure Claude Code with the MCP

Register the MCP server with Claude Code:
```bash
claude mcp add nil-pro nil-pro-mcp
```

The MCP server defaults to `http://localhost:8000` so no extra environment variables are needed for local dev.

**Verify:**
```bash
claude mcp list
```
You should see `nil-pro` in the list.

---

## Step 8 — Verify Everything Works

Make sure the backend is still running (Step 5), then start Claude Code from the repo root:
```bash
cd /path/to/realgm-scraper
claude
```

In the Claude Code prompt, type:
```
Search for Cooper Flagg in NIL PRO
```

Claude should call the NIL PRO tools and return player data. You'll see tool calls like `search_players` in the output.

---

## Daily Workflow

Each time you work on the project:

1. **Start the backend** (in one terminal tab):
   ```bash
   cd realgm-scraper/backend
   source venv/bin/activate
   uvicorn main:app --reload --port 8000
   ```

2. **Start Claude Code** (in another tab):
   ```bash
   cd realgm-scraper
   claude
   ```

---

## Troubleshooting

**`pip install -r requirements.txt` fails on psycopg2**
Run: `brew install libpq` then retry.

**`nil-pro-mcp: command not found` after installing**
The pip scripts directory may not be on your PATH. Run:
```bash
python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))"
```
Add that path to your `~/.zshrc` and reopen Terminal.

**Backend starts but returns empty results**
Double-check the `DATABASE_URL` in `backend/.env` — make sure it's the full Neon connection string and there are no extra spaces or missing characters.

**Claude Code doesn't call the NIL PRO tools**
Run `claude mcp list` and confirm `nil-pro` appears. If not, re-run Step 7.
