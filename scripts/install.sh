#!/usr/bin/env bash
# ast-outline one-command installer for macOS / Linux.
#
# Usage:
#   curl -LsSf https://raw.githubusercontent.com/ast-outline/ast-outline/main/scripts/install.sh | bash
#
# This installs:
#   1. `uv` (if missing) — the Python package manager we use.
#   2. `ast-outline` globally as a uv-managed tool.
#
# Uninstall later with: uv tool uninstall ast-outline

set -euo pipefail

REPO_URL="${AST_OUTLINE_REPO:-https://github.com/ast-outline/ast-outline.git}"
REF="${AST_OUTLINE_REF:-main}"

say() { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m==>\033[0m %s\n' "$*" >&2; }
fail() { printf '\033[1;31m==>\033[0m %s\n' "$*" >&2; exit 1; }

# 1. Ensure uv is available ------------------------------------------------

if ! command -v uv >/dev/null 2>&1; then
    say "uv not found — installing (https://docs.astral.sh/uv/)"
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Add uv's bin dir to PATH for this session
    if [ -d "$HOME/.local/bin" ]; then
        export PATH="$HOME/.local/bin:$PATH"
    fi
    if [ -d "$HOME/.cargo/bin" ]; then
        export PATH="$HOME/.cargo/bin:$PATH"
    fi

    if ! command -v uv >/dev/null 2>&1; then
        fail "uv was installed but is not on PATH. Open a new shell and re-run this script, or install ast-outline manually with: uv tool install git+$REPO_URL"
    fi
else
    say "uv already installed: $(uv --version)"
fi

# 2. Install ast-outline ---------------------------------------------------

say "installing ast-outline from $REPO_URL (ref: $REF)"
uv tool install --force "git+$REPO_URL@$REF"

# 3. Verify ---------------------------------------------------------------

if command -v ast-outline >/dev/null 2>&1; then
    say "installed successfully:"
    ast-outline --help | head -6 || true
    echo
    say "try:  ast-outline help"
else
    warn "ast-outline is installed but not yet on PATH."
    warn "add this to your shell profile:"
    warn '    export PATH="$HOME/.local/bin:$PATH"'
    warn "then restart your terminal."
fi
