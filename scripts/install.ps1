# ast-outline one-command installer for Windows (PowerShell).
#
# Usage:
#   iwr -useb https://raw.githubusercontent.com/dim-s/ast-outline/main/scripts/install.ps1 | iex
#
# This installs:
#   1. `uv` (if missing) - the Python package manager we use.
#   2. `ast-outline` globally as a uv-managed tool.
#      A backward-compat `code-outline` CLI alias is also installed for
#      users coming from the pre-0.3.0 name.
#
# Uninstall later with:  uv tool uninstall ast-outline

$ErrorActionPreference = 'Stop'

# Accept both new and legacy env-var names so migration is seamless.
$RepoUrl =
    if ($env:AST_OUTLINE_REPO)  { $env:AST_OUTLINE_REPO }
    elseif ($env:CODE_OUTLINE_REPO) { $env:CODE_OUTLINE_REPO }
    else { 'https://github.com/dim-s/ast-outline.git' }
$Ref =
    if ($env:AST_OUTLINE_REF)  { $env:AST_OUTLINE_REF }
    elseif ($env:CODE_OUTLINE_REF) { $env:CODE_OUTLINE_REF }
    else { 'main' }

function Say($msg) { Write-Host "==> $msg" -ForegroundColor Green }
function Warn($msg) { Write-Host "==> $msg" -ForegroundColor Yellow }
function Fail($msg) { Write-Host "==> $msg" -ForegroundColor Red; exit 1 }

# 1. Ensure uv is available ---------------------------------------------

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Say "uv not found - installing (https://docs.astral.sh/uv/)"
    try {
        powershell -ExecutionPolicy ByPass -NoProfile -Command "irm https://astral.sh/uv/install.ps1 | iex"
    } catch {
        Fail "failed to install uv: $_"
    }

    # Refresh PATH for this session
    $localBin = Join-Path $env:USERPROFILE '.local\bin'
    if (Test-Path $localBin) {
        $env:Path = "$localBin;$env:Path"
    }

    if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
        Fail "uv was installed but is not on PATH. Open a new PowerShell window and re-run this script, or install ast-outline manually with: uv tool install git+$RepoUrl"
    }
} else {
    Say ("uv already installed: " + (uv --version))
}

# 2. Install ast-outline ------------------------------------------------

Say "installing ast-outline from $RepoUrl (ref: $Ref)"
uv tool install --force "git+$RepoUrl@$Ref"

# 3. Verify -------------------------------------------------------------

if (Get-Command ast-outline -ErrorAction SilentlyContinue) {
    Say "installed successfully:"
    ast-outline --help | Select-Object -First 6
    Write-Host ""
    Say "try:  ast-outline help"
    Say "(legacy ``code-outline`` command is also installed as an alias)"
} else {
    Warn "ast-outline is installed but not yet on PATH."
    Warn "add this to your PowerShell profile:"
    Warn '    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"'
    Warn "then restart your terminal."
}
