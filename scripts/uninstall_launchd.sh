#!/usr/bin/env bash
# =============================================================================
# LeetCode Lab — macOS LaunchAgent Uninstaller
# =============================================================================
# Stops and removes the LeetCode Lab background server agent.
#
# Usage:
#   ./scripts/uninstall_launchd.sh
#
# Safe to run even if the agent is not currently loaded.
# =============================================================================

set -euo pipefail

LABEL="com.rajwav.leetcode-lab"
PLIST_NAME="${LABEL}.plist"
PLIST_DEST="${HOME}/Library/LaunchAgents/${PLIST_NAME}"
GUI_DOMAIN="gui/$(id -u)"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║          LeetCode Lab — LaunchAgent Uninstaller          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ---- Unload agent -----------------------------------------------------------

if launchctl list "${LABEL}" &>/dev/null 2>&1; then
    echo "[INFO] Stopping and unloading agent: ${LABEL}"
    if launchctl bootout "${GUI_DOMAIN}" "${PLIST_DEST}" 2>/dev/null; then
        echo "[INFO] Agent bootout succeeded."
    elif launchctl unload -w "${PLIST_DEST}" 2>/dev/null; then
        echo "[INFO] Agent unloaded (legacy launchctl unload)."
    else
        echo "[WARN] Could not unload agent cleanly. It may still be running."
        echo "       Kill manually: kill \$(launchctl list ${LABEL} | grep PID | awk '{print \$3}')"
    fi
else
    echo "[INFO] Agent '${LABEL}' is not currently loaded — nothing to unload."
fi

# ---- Remove plist -----------------------------------------------------------

if [[ -f "${PLIST_DEST}" ]]; then
    rm -f "${PLIST_DEST}"
    echo "[INFO] Removed plist: ${PLIST_DEST}"
else
    echo "[INFO] Plist not found at ${PLIST_DEST} — already removed."
fi

echo ""
echo "[INFO] Uninstall complete. The server will no longer start on login."
echo "       To reinstall: ./scripts/install_launchd.sh"
echo ""
