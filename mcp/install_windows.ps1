# NIL PRO MCP - Windows Installer
# Usage: Right-click this file -> "Run with PowerShell"
#   OR open PowerShell and run: .\install_windows.ps1

$ErrorActionPreference = "Stop"

Write-Host "=== NIL PRO MCP Installer (Windows) ===" -ForegroundColor Cyan
Write-Host ""

# 1. Check Python
try {
    $pythonVersion = python --version 2>&1
} catch {
    Write-Host "ERROR: Python is not installed or not in PATH." -ForegroundColor Red
    Write-Host "Download it from https://www.python.org/downloads/"
    Write-Host "Make sure to check 'Add Python to PATH' during install."
    Read-Host "Press Enter to exit"
    exit 1
}

$minorVersion = python -c "import sys; print(sys.version_info.minor)"
if ([int]$minorVersion -lt 10) {
    Write-Host "ERROR: Python 3.10 or higher is required." -ForegroundColor Red
    Write-Host "Download a newer version from https://www.python.org/downloads/"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "OK Python found: $pythonVersion" -ForegroundColor Green

# 2. Install the package
Write-Host ""
Write-Host "Installing nil-pro-mcp..."
python -m pip install --quiet --upgrade "git+https://github.com/jzhang621/realgm-scraper.git#subdirectory=mcp"

# 3. Find the installed command path
$cmd = (where.exe nil-pro-mcp 2>$null) | Select-Object -First 1

if (-not $cmd) {
    # Fallback: find via Python scripts dir
    $scriptsDir = python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
    $cmd = Join-Path $scriptsDir "nil-pro-mcp.exe"
}

if (-not (Test-Path $cmd)) {
    Write-Host "ERROR: nil-pro-mcp was installed but could not be located." -ForegroundColor Red
    Write-Host "Try running: pip show nil-pro-mcp"
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "OK Installed at: $cmd" -ForegroundColor Green

# 4. Update Claude Desktop config
$configDir  = Join-Path $env:APPDATA "Claude"
$configFile = Join-Path $configDir "claude_desktop_config.json"

if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir | Out-Null
}

if (Test-Path $configFile) {
    $config = Get-Content $configFile -Raw | ConvertFrom-Json
} else {
    $config = [PSCustomObject]@{}
}

# Add mcpServers if missing
if (-not (Get-Member -InputObject $config -Name "mcpServers" -MemberType NoteProperty)) {
    $config | Add-Member -NotePropertyName "mcpServers" -NotePropertyValue ([PSCustomObject]@{})
}

# Add nil-pro server entry
$nilProEntry = [PSCustomObject]@{
    command = $cmd
    env     = [PSCustomObject]@{
        NIL_PRO_API_URL = "https://realgm-scraper.onrender.com"
    }
}

$config.mcpServers | Add-Member -NotePropertyName "nil-pro" -NotePropertyValue $nilProEntry -Force

# Save back to file
$config | ConvertTo-Json -Depth 10 | Set-Content -Path $configFile -Encoding UTF8

Write-Host "OK Claude Desktop config updated: $configFile" -ForegroundColor Green

Write-Host ""
Write-Host "=== Done! ===" -ForegroundColor Cyan
Write-Host "Restart Claude Desktop to activate the NIL PRO tools."
Write-Host ""
Read-Host "Press Enter to exit"
