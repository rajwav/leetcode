#!/usr/bin/env bash
# =============================================================================
# LeetCode Lab — LaunchAgent Status Checker
# =============================================================================
# Shows the current state of the background ingestion server.
#
# Usage:
#   ./scripts/status_launchd.sh
# =============================================================================

LABEL="com.rajwav.leetcode-lab"
LOG_DIR="${HOME}/Library/Logs/LeetCodeLab"
LOG_OUT="${LOG_DIR}/server.out"
LOG_ERR="${LOG_DIR}/server.err"
PLIST_DEST="${HOME}/Library/LaunchAgents/${LABEL}.plist"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}║             LeetCode Lab — Server Status                 ║${NC}"
echo -e "${BOLD}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

# ---- Agent status -----------------------------------------------------------

LAUNCHD_INFO="$(launchctl list "${LABEL}" 2>/dev/null || true)"

if [[ -z "${LAUNCHD_INFO}" ]]; then
    echo -e "${RED}[STOPPED]${NC} LaunchAgent '${LABEL}' is not loaded."
    echo ""
    if [[ -f "${PLIST_DEST}" ]]; then
        echo -e "${YELLOW}  Plist exists but agent is not running.${NC}"
        echo "  Try: launchctl bootstrap gui/\$(id -u) ${PLIST_DEST}"
    else
        echo "  Run ./scripts/install_launchd.sh to install."
    fi
else
    PID="$(echo "${LAUNCHD_INFO}" | grep '"PID"' | awk '{print $3}' | tr -d ',')"
    EXIT_STATUS="$(echo "${LAUNCHD_INFO}" | grep '"LastExitStatus"' | awk '{print $3}' | tr -d ',')"

    if [[ -n "${PID}" && "${PID}" != "0" ]]; then
        echo -e "${GREEN}[RUNNING]${NC} PID ${PID} — http://127.0.0.1:8765"
        # Quick health check
        if curl -sf http://127.0.0.1:8765/ &>/dev/null; then
            echo -e "${GREEN}[HEALTHY]${NC} Server responding at http://127.0.0.1:8765/"
        else
            echo -e "${YELLOW}[WARN]${NC}    Server process is running but not responding on port 8765."
        fi
    else
        echo -e "${RED}[CRASHED]${NC} Agent is registered but not running (last exit: ${EXIT_STATUS:-unknown})"
        echo "  launchd will restart it after ThrottleInterval (10s)."
        echo "  If crashing repeatedly, check error log:"
        echo "    tail -50 ${LOG_ERR}"
    fi
fi

# ---- Plist ------------------------------------------------------------------

echo ""
echo -e "${CYAN}── Plist ──────────────────────────────────────────────────${NC}"
if [[ -f "${PLIST_DEST}" ]]; then
    echo "  Installed : ${PLIST_DEST}"
    PYTHON_LINE="$(grep -A1 '<key>ProgramArguments</key>' "${PLIST_DEST}" | grep string | head -1 | sed 's/.*<string>\(.*\)<\/string>.*/\1/')"
    echo "  Python    : ${PYTHON_LINE}"
else
    echo "  Not installed. Run ./scripts/install_launchd.sh"
fi

# ---- Logs -------------------------------------------------------------------

echo ""
echo -e "${CYAN}── Recent stdout (server.out) ─────────────────────────────${NC}"
if [[ -f "${LOG_OUT}" ]]; then
    tail -20 "${LOG_OUT}" | sed 's/^/  /'
else
    echo "  (no log yet — server has not started or no output produced)"
fi

echo ""
echo -e "${CYAN}── Recent stderr (server.err) ─────────────────────────────${NC}"
if [[ -f "${LOG_ERR}" ]]; then
    tail -10 "${LOG_ERR}" | sed 's/^/  /'
else
    echo "  (no errors logged)"
fi

echo ""
echo -e "${CYAN}── Commands ───────────────────────────────────────────────${NC}"
echo "  Install   : ./scripts/install_launchd.sh"
echo "  Uninstall : ./scripts/uninstall_launchd.sh"
echo "  Full log  : tail -f ${LOG_OUT}"
echo "  Error log : tail -f ${LOG_ERR}"
echo ""
