#!/usr/bin/env bash
# =============================================================================
# LeetCode Lab — macOS LaunchAgent Installer
# =============================================================================
# Installs a launchd user agent that automatically starts the LeetCode Lab
# ingestion server on macOS login.
#
# Usage:
#   ./scripts/install_launchd.sh
#
# What it does:
#   1. Detects the correct Python interpreter
#   2. Resolves the repository root (absolute path)
#   3. Expands the plist template with real values
#   4. Installs to ~/Library/LaunchAgents/
#   5. Loads the agent immediately (no reboot required)
#
# Safety: Does NOT modify any git repository, source code, or solutions.
# =============================================================================

set -euo pipefail

LABEL="com.rajwav.leetcode-lab"
PLIST_NAME="${LABEL}.plist"
PLIST_DEST="${HOME}/Library/LaunchAgents/${PLIST_NAME}"
LOG_DIR="${HOME}/Library/Logs/LeetCodeLab"

# ---- Resolve paths ----------------------------------------------------------

# Repository root = directory containing this script's parent
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
TEMPLATE="${SCRIPT_DIR}/launchd/${LABEL}.plist.template"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║           LeetCode Lab — LaunchAgent Installer           ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ---- Sanity checks ----------------------------------------------------------

if [[ ! -f "${TEMPLATE}" ]]; then
    echo "[ERROR] Plist template not found: ${TEMPLATE}"
    echo "        Are you running from inside the LeetCode Lab repository?"
    exit 1
fi

if [[ ! -f "${REPO_ROOT}/scripts/lab.py" ]]; then
    echo "[ERROR] scripts/lab.py not found at: ${REPO_ROOT}/scripts/lab.py"
    echo "        Repository root detected as: ${REPO_ROOT}"
    exit 1
fi

# ---- Detect Python ----------------------------------------------------------

# Prefer standard system/homebrew python3 over a temporary venv for the daemon
if [[ -z "${PYTHON_BIN:-}" ]]; then
    if [[ -x "/usr/local/bin/python3" ]]; then
        PYTHON_BIN="/usr/local/bin/python3"
    elif [[ -x "/opt/homebrew/bin/python3" ]]; then
        PYTHON_BIN="/opt/homebrew/bin/python3"
    elif [[ -x "/usr/bin/python3" ]]; then
        PYTHON_BIN="/usr/bin/python3"
    else
        PYTHON_BIN="$(which python3 2>/dev/null || true)"
    fi
fi

if [[ -z "${PYTHON_BIN}" ]]; then
    echo "[ERROR] python3 not found in PATH."
    echo "        Set PYTHON_BIN manually: PYTHON_BIN=/path/to/python3 ./scripts/install_launchd.sh"
    exit 1
fi

# Resolve to absolute path
PYTHON_BIN="$(cd "$(dirname "${PYTHON_BIN}")" && pwd)/$(basename "${PYTHON_BIN}")"

# Verify it can run lab.py
if ! "${PYTHON_BIN}" "${REPO_ROOT}/scripts/lab.py" stats &>/dev/null; then
    echo "[WARN] Python at ${PYTHON_BIN} could not run lab.py stats."
    echo "       Continuing anyway — check logs after install."
fi

echo "[INFO] Python interpreter : ${PYTHON_BIN}"
echo "[INFO] Repository root    : ${REPO_ROOT}"
echo "[INFO] Plist destination  : ${PLIST_DEST}"
echo "[INFO] Log directory      : ${LOG_DIR}"
echo ""

# ---- Guard: already installed -----------------------------------------------

if launchctl list "${LABEL}" &>/dev/null 2>&1; then
    echo "[WARN] LaunchAgent '${LABEL}' is already loaded."
    echo "       To reinstall, run ./scripts/uninstall_launchd.sh first."
    echo "       To check status, run ./scripts/status_launchd.sh"
    exit 0
fi

if [[ -f "${PLIST_DEST}" ]]; then
    echo "[WARN] Plist already exists at ${PLIST_DEST} but agent is not loaded."
    echo "       Overwriting and reloading..."
fi

# ---- Expand template --------------------------------------------------------

USERNAME="$(id -un)"

mkdir -p "$(dirname "${PLIST_DEST}")"
mkdir -p "${LOG_DIR}"

sed \
    -e "s|__PYTHON__|${PYTHON_BIN}|g" \
    -e "s|__REPO_ROOT__|${REPO_ROOT}|g" \
    -e "s|__USER__|${USERNAME}|g" \
    "${TEMPLATE}" > "${PLIST_DEST}"

echo "[INFO] Plist written to: ${PLIST_DEST}"

# ---- Validate plist syntax --------------------------------------------------

if ! plutil -lint "${PLIST_DEST}" &>/dev/null; then
    echo "[ERROR] Generated plist failed plutil lint check."
    echo "        Inspect: ${PLIST_DEST}"
    rm -f "${PLIST_DEST}"
    exit 1
fi

echo "[INFO] Plist syntax validated (plutil OK)"

# ---- Load agent (no reboot required) ----------------------------------------

# Use 'bootstrap' for macOS 10.11+ (preferred over deprecated launchctl load)
GUI_DOMAIN="gui/$(id -u)"

if launchctl bootstrap "${GUI_DOMAIN}" "${PLIST_DEST}" 2>/dev/null; then
    echo "[INFO] LaunchAgent loaded into domain: ${GUI_DOMAIN}"
elif launchctl load -w "${PLIST_DEST}" 2>/dev/null; then
    echo "[INFO] LaunchAgent loaded (legacy launchctl load)"
else
    echo "[WARN] Could not load agent immediately. It will start on next login."
    echo "       To load manually: launchctl bootstrap ${GUI_DOMAIN} ${PLIST_DEST}"
fi

# ---- Summary ----------------------------------------------------------------

sleep 1
echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║                    INSTALL COMPLETE                      ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
echo "  The LeetCode Lab server will now start automatically"
echo "  on every macOS login."
echo ""
echo "  Server: http://127.0.0.1:8765"
echo "  Logs:   ${LOG_DIR}/server.out"
echo "          ${LOG_DIR}/server.err"
echo ""
echo "  Check status:  ./scripts/status_launchd.sh"
echo "  Uninstall:     ./scripts/uninstall_launchd.sh"
echo ""
