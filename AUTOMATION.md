# LeetCode Lab — Automation Guide

> **One-time setup. Then you only solve LeetCode.**

---

## Architecture

```
macOS Login
    ↓
launchd (com.rajwav.leetcode-lab)
    ↓  auto-restarts on crash, 10s throttle
python3 scripts/lab.py listen --push
    ↓  binds 127.0.0.1:8765 only
    ↓  logs → ~/Library/Logs/LeetCodeLab/
    │
LeetCode → Submit → Accepted
    ↓
Tampermonkey userscript v1.2.0
    ↓  hooks fetch + XHR in page Main World
POST http://127.0.0.1:8765/ingest
    ↓  origin check · size limit · JSON validation
validate_submission()
    ↓  slug safety · language normalization · status check
ProblemManager.import_submission()
    ↓  idempotent write · non-destructive README
DashboardUpdater.update_all()
    ↓  delimiter-bounded README.md + PROGRESS.md
GitManager.stage_submission()
    ↓  allowlist-only · foreign-file detection
GitManager.commit()
    ↓  final safety check on staged content
GitManager.push()           ← ALL of these checks run every time:
    ↓  branch == main?      ✓
    ↓  origin configured?   ✓
    ↓  remote diverged?     ✓ (refuses non-fast-forward)
    ↓  no force push        ✓
github.com/rajwav/leetcode  🚀
```

---

## One-Time Setup

### 1. Install the Tampermonkey browser extension

- [Chrome](https://chrome.google.com/webstore/detail/tampermonkey/dhdgffkkebhmkfjojejmpbldmpobfkfo)
- [Firefox](https://addons.mozilla.org/en-US/firefox/addon/tampermonkey/)

### 2. Install the userscript

Open Tampermonkey → Dashboard → New Script.
Paste the entire contents of:

```
scripts/userscript/leetcode-lab-sync.user.js
```

Save. Tampermonkey will automatically inject it on `leetcode.com/problems/*`.

### 3. Install the background server (LaunchAgent)

```bash
cd /Users/raj/Desktop/Leetcode
./scripts/install_launchd.sh
```

That's it. The server starts immediately and will start automatically on every future login.

---

## Daily Workflow

```
Mac login
    ↓ (automatic — no action needed)
LeetCode Lab server starts on 127.0.0.1:8765

Open https://leetcode.com
    ↓
Solve a problem
    ↓
Submit → Accepted
    ↓ (automatic — no action needed)
🟢 Toast: "LeetCode Lab synced — 0001-two-sum"

problems/easy/0001-two-sum/
├── solution.cpp     ← your code
└── README.md        ← problem metadata

README.md + PROGRESS.md updated
    ↓
Git commit: feat(problems): add 0001-two-sum [Easy] [cpp]
    ↓
git push origin main
    ↓
github.com/rajwav/leetcode 🚀
```

You never open a terminal. You never run a command. You only solve LeetCode.

---

## Troubleshooting

### Check server status
```bash
./scripts/status_launchd.sh
```

### View live logs
```bash
# stdout (ingestion activity)
tail -f ~/Library/Logs/LeetCodeLab/server.out

# stderr (errors)
tail -f ~/Library/Logs/LeetCodeLab/server.err
```

### Server not starting?
```bash
# Check launchd registration
launchctl list | grep leetcode-lab

# Check for port conflicts
lsof -i :8765

# Reinstall
./scripts/uninstall_launchd.sh
./scripts/install_launchd.sh
```

### Toast shows red 🔴 after Accepted submission
The submission was captured but the server returned an error.
Check the error log:
```bash
tail -50 ~/Library/Logs/LeetCodeLab/server.err
```

Common causes:
- **Git safety error**: branch not `main`, or remote diverged — pull first
- **Delimiter error**: README.md automation delimiters are corrupted — inspect the file
- **Push failed**: GitHub authentication expired — re-authenticate `gh auth login`

### Userscript not firing?
1. Check Tampermonkey is enabled on `leetcode.com`
2. Check the script is installed and enabled (green pill in Tampermonkey icon)
3. Open browser DevTools Console, look for `[LeetCode Lab Bridge]` messages
4. If needed, temporarily enable debug: find `DEBUG: false` in the script and set to `true`

### Submission captured but not pushed?
The local commit exists — the push safety check rejected it.
Check the log:
```bash
grep "GitSafetyError\|push" ~/Library/Logs/LeetCodeLab/server.err | tail -20
```

The commit is safe on disk. To push manually:
```bash
git push origin main
```

---

## Uninstall

```bash
./scripts/uninstall_launchd.sh
```

This stops the server and removes the LaunchAgent. Your solutions, commits, and repository are untouched.

---

## Security Model

| Guarantee | How |
| :--- | :--- |
| Server listens on loopback only | `run_server()` enforces `127.0.0.1` — throws `ValueError` otherwise |
| Origin allowlist | Only `leetcode.com` and `leetcode.cn` accepted |
| No credentials in userscript | Userscript only POSTs to `127.0.0.1` — never to GitHub |
| No force push | `GitManager.push()` never uses `--force` |
| No unexpected staged files | `check_no_foreign_staged_files()` aborts if your work is staged |
| Allowlist-only staging | Only `problems/`, `README.md`, `PROGRESS.md` can be staged |
| Transactional dashboard | README.md + PROGRESS.md are backed up before write; restored on failure |
| Concurrency | `_INGEST_LOCK` serializes concurrent browser tab submissions |

---

## File Reference

| File | Purpose |
| :--- | :--- |
| `scripts/lab.py` | Main CLI: `listen`, `import`, `validate`, `stats`, `test` |
| `scripts/server.py` | HTTP ingestion server |
| `scripts/engine/validator.py` | Payload schema validation |
| `scripts/engine/problem_manager.py` | Problem directory + README management |
| `scripts/engine/statistics.py` | Dashboard statistics + updater |
| `scripts/engine/git_manager.py` | Safe Git operations |
| `scripts/userscript/leetcode-lab-sync.user.js` | Tampermonkey browser adapter |
| `scripts/launchd/com.rajwav.leetcode-lab.plist.template` | LaunchAgent template |
| `scripts/install_launchd.sh` | Install background server |
| `scripts/uninstall_launchd.sh` | Uninstall background server |
| `scripts/status_launchd.sh` | Check server status + logs |
| `PROGRESS.md` | Auto-updated problem log and statistics |

---

*This system was designed to be a personal DSA operating system. You solve problems. The infrastructure handles everything else.*
