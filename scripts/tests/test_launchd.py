"""
Tests for the macOS LaunchAgent infrastructure (Phase 1).

These tests verify the static correctness of the plist template and shell
scripts without actually installing or running any launchd agents.
All tests are file-inspection based — safe to run in any environment.
"""

import os
import re
import stat
from pathlib import Path
import unittest

# Repository root is two levels above this file's directory
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
LAUNCHD_DIR = SCRIPTS_DIR / "launchd"
PLIST_TEMPLATE = LAUNCHD_DIR / "com.rajwav.leetcode-lab.plist.template"
INSTALL_SCRIPT = SCRIPTS_DIR / "install_launchd.sh"
UNINSTALL_SCRIPT = SCRIPTS_DIR / "uninstall_launchd.sh"
STATUS_SCRIPT = SCRIPTS_DIR / "status_launchd.sh"
EXPECTED_LABEL = "com.rajwav.leetcode-lab"


def read_plist() -> str:
    return PLIST_TEMPLATE.read_text(encoding="utf-8")


def read_install() -> str:
    return INSTALL_SCRIPT.read_text(encoding="utf-8")


def read_uninstall() -> str:
    return UNINSTALL_SCRIPT.read_text(encoding="utf-8")


class TestLaunchdFiles(unittest.TestCase):

    # 1. All expected files exist
    def test_plist_template_exists(self):
        self.assertTrue(PLIST_TEMPLATE.exists(), f"Missing: {PLIST_TEMPLATE}")

    def test_install_script_exists(self):
        self.assertTrue(INSTALL_SCRIPT.exists(), f"Missing: {INSTALL_SCRIPT}")

    def test_uninstall_script_exists(self):
        self.assertTrue(UNINSTALL_SCRIPT.exists(), f"Missing: {UNINSTALL_SCRIPT}")

    def test_status_script_exists(self):
        self.assertTrue(STATUS_SCRIPT.exists(), f"Missing: {STATUS_SCRIPT}")

    # 2. Shell scripts are executable
    def test_install_script_is_executable(self):
        mode = INSTALL_SCRIPT.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR, "install_launchd.sh is not executable by owner")

    def test_uninstall_script_is_executable(self):
        mode = UNINSTALL_SCRIPT.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR, "uninstall_launchd.sh is not executable by owner")

    def test_status_script_is_executable(self):
        mode = STATUS_SCRIPT.stat().st_mode
        self.assertTrue(mode & stat.S_IXUSR, "status_launchd.sh is not executable by owner")

    # 3. Plist contains correct label
    def test_plist_label_is_correct(self):
        content = read_plist()
        self.assertIn(f"<string>{EXPECTED_LABEL}</string>", content,
                      "Plist label does not match expected value")

    # 4. Plist has KeepAlive = true (auto-restart on crash)
    def test_plist_keepalive_true(self):
        content = read_plist()
        # KeepAlive key must be followed by <true/>
        match = re.search(r"<key>KeepAlive</key>\s*<(true|false)/>", content)
        self.assertIsNotNone(match, "KeepAlive key not found in plist")
        self.assertEqual(match.group(1), "true", "KeepAlive must be true for crash recovery")

    # 5. Plist has RunAtLoad = true (starts on login)
    def test_plist_run_at_load_true(self):
        content = read_plist()
        match = re.search(r"<key>RunAtLoad</key>\s*<(true|false)/>", content)
        self.assertIsNotNone(match, "RunAtLoad key not found in plist")
        self.assertEqual(match.group(1), "true", "RunAtLoad must be true")

    # 6. ProgramArguments contain 'listen' and '--push'
    def test_plist_args_contain_listen_and_push(self):
        content = read_plist()
        self.assertIn("<string>listen</string>", content,
                      "ProgramArguments must contain 'listen'")
        self.assertIn("<string>--push</string>", content,
                      "ProgramArguments must contain '--push' for auto-push")

    # 7. ProgramArguments use template tokens (not hardcoded paths)
    def test_plist_uses_template_tokens(self):
        content = read_plist()
        self.assertIn("__PYTHON__", content,
                      "Plist must use __PYTHON__ token (replaced at install time)")
        self.assertIn("__REPO_ROOT__", content,
                      "Plist must use __REPO_ROOT__ token (replaced at install time)")
        self.assertIn("__USER__", content,
                      "Plist must use __USER__ token (replaced at install time)")

    # 8. Plist does NOT bind to 0.0.0.0 (loopback only)
    def test_plist_does_not_expose_to_network(self):
        content = read_plist()
        self.assertNotIn("0.0.0.0", content,
                         "Plist must not expose server to network — loopback only")

    # 9. Plist has StandardOutPath and StandardErrorPath (log files)
    def test_plist_log_paths_configured(self):
        content = read_plist()
        self.assertIn("<key>StandardOutPath</key>", content,
                      "Plist must define StandardOutPath for log capture")
        self.assertIn("<key>StandardErrorPath</key>", content,
                      "Plist must define StandardErrorPath for error log capture")
        self.assertIn("LeetCodeLab", content,
                      "Log paths must reference LeetCodeLab log directory")

    # 10. Plist has ThrottleInterval to prevent rapid crash loops
    def test_plist_has_throttle_interval(self):
        content = read_plist()
        self.assertIn("<key>ThrottleInterval</key>", content,
                      "Plist must have ThrottleInterval to prevent crash loops")

    # 11. Install script uses 'launchctl bootstrap' (modern macOS API)
    def test_install_script_uses_bootstrap(self):
        content = read_install()
        self.assertIn("launchctl bootstrap", content,
                      "install_launchd.sh must use 'launchctl bootstrap' for modern macOS")

    # 12. Install script uses 'plutil -lint' for plist validation
    def test_install_script_validates_plist(self):
        content = read_install()
        self.assertIn("plutil", content,
                      "install_launchd.sh should validate plist with plutil")

    # 13. Uninstall script uses 'launchctl bootout' (modern macOS API)
    def test_uninstall_script_uses_bootout(self):
        content = read_uninstall()
        self.assertIn("launchctl bootout", content,
                      "uninstall_launchd.sh must use 'launchctl bootout' for modern macOS")

    # 14. Install script creates log directory
    def test_install_script_creates_log_dir(self):
        content = read_install()
        self.assertIn("mkdir -p", content, "install_launchd.sh must create log directory")
        self.assertIn("LeetCodeLab", content, "Log directory must be LeetCodeLab")

    # 15. Install script guards against double-install
    def test_install_script_has_guard_against_double_install(self):
        content = read_install()
        self.assertIn("already loaded", content,
                      "install_launchd.sh must detect and warn if agent is already loaded")

    # 16. Plist EnvironmentVariables sets PATH (not empty)
    def test_plist_environment_path_set(self):
        content = read_plist()
        self.assertIn("<key>PATH</key>", content,
                      "Plist must set PATH in EnvironmentVariables for launchd shell resolution")

    # 17. Plist does NOT contain actual credential strings
    def test_plist_template_contains_no_secrets(self):
        content = read_plist()
        # These patterns indicate actual credential values, not legitimate template words.
        # 'token' is legitimately used in the comment "Token substitution performed at install time"
        # so we check for token assignment patterns instead.
        forbidden_patterns = [
            r"ghp_[A-Za-z0-9]{36}",            # GitHub PAT format
            r"password\s*=",                     # password assignment
            r"api_key\s*=",                      # api_key assignment
            r"secret\s*=",                       # secret assignment
            r"-----BEGIN (RSA|EC|OPENSSH)",      # private key header
            r"['\"]token['\"]:\s*['\"]",         # JSON token field
        ]
        for pat in forbidden_patterns:
            import re as _re
            self.assertIsNone(
                _re.search(pat, content, _re.IGNORECASE),
                f"Plist template appears to contain a credential matching pattern: {pat}"
            )

    # 18. lab.py listen command wires correctly (signal and port-in-use handling)
    def test_lab_listen_has_sigterm_handler(self):
        lab_py = (SCRIPTS_DIR / "lab.py").read_text(encoding="utf-8")
        self.assertIn("signal.SIGTERM", lab_py,
                      "lab.py cmd_listen must register a SIGTERM handler for launchd")

    # 19. lab.py listen handles port-in-use gracefully
    def test_lab_listen_handles_port_in_use(self):
        lab_py = (SCRIPTS_DIR / "lab.py").read_text(encoding="utf-8")
        self.assertIn("Address already in use", lab_py,
                      "lab.py must handle OSError 'Address already in use' with a clean message")

    # 20. server.py has configure_logging and log_startup
    def test_server_has_configure_logging(self):
        server_py = (SCRIPTS_DIR / "server.py").read_text(encoding="utf-8")
        self.assertIn("def configure_logging", server_py,
                      "server.py must export configure_logging() for launchd use")
        self.assertIn("def log_startup", server_py,
                      "server.py must export log_startup() for structured launchd logs")


if __name__ == "__main__":
    unittest.main()
