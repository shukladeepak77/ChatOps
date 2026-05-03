# ChatOps Manual Test Plan — Browser Execution Guide

## Setup

1. Open your browser on Windows
2. Navigate to the ChatOps URL (e.g. `http://<server-ip>:8001/chatops`)
3. You should see the **ChatOps Console** with a chat input at the bottom
4. Type each message exactly as shown and compare the response

**How to mark results:**
- ✅ PASS — response matches the expected output
- ❌ FAIL — response is missing expected content or shows an error

**Note:** Values like percentages, port numbers, process names, and timestamps
will differ on your machine — focus on the **keywords and structure**, not exact numbers.

---

## Section 1 — Help & Welcome

---

### TC-01 · Hint Text in Header Bar

**Action:** Open the chatbot URL in the browser (no typing needed)

**Expected — blue header bar shows:**
```
ChatOps Console
disk · memory · cpu · health · ports · type help for all commands
```

The hint text appears as a small subtitle line directly below the title inside the blue bar.
The word **help** appears slightly brighter than the rest.

If you have previously used the chatbot, old messages appear in the chat window below a
`— previous session —` divider. The chat window itself has NO automatic welcome bubble.

**Pass if:**
- Hint text is visible in the blue header (not in the chat window)
- Chat window opens directly at the last message (no scrolling past a welcome bubble)
- Previous session messages are separated by the `— previous session —` label

---

### TC-02 · Help Command

**Type:** `help`

**Expected response:**
```
Commands:
  check disk | check memory | check cpu | check uptime | check ports
  top processes | system health | analyze logs: <content>
  show alerts | list runbooks | run <runbook> | confirm <runbook> | cancel
  run tests | config | help
```

**Pass if:** Response lists all commands including `check disk`, `check cpu`, `top processes`, `run tests`.

---

### TC-03 · Empty Message

**Type:** *(press Enter with nothing typed — or just a space)*

**Expected:** Nothing happens. No message bubble is added to the chat. The input box stays empty and focused.

**Pass if:** The chat window does not change when Enter is pressed on a blank or whitespace-only input.

---

## Section 2 — Disk Monitoring

---

### TC-04 · Check Disk (exact command)

**Type:** `check disk`

**Expected response:**
```
Disk: XX.X% used (X.X GB / XX.X GB) — OK
```
*(Status will be OK / WARNING / CRITICAL depending on actual disk usage)*

**Pass if:** Response starts with `Disk:`, contains `%`, `GB`, and ends with a status word (`OK`, `WARNING`, or `CRITICAL`).

---

### TC-05 · Check Disk (natural language)

**Type:** `how full is my disk`

**Expected response:** Same structure as TC-04
```
Disk: XX.X% used (X.X GB / XX.X GB) — OK
```

**Pass if:** Response contains `Disk:` and a percentage.

> **Note:** The phrase `"how full"` is what routes this correctly — so `how full is my disk`,
> `how full is my drive`, or even `how full is my desk` (typo) all return disk info.

---

### TC-06 · Check Disk (alternate phrasing)

**Type:** `disk space`

**Expected response:** Same structure as TC-04

**Pass if:** Response contains `Disk:` and a percentage.

---

### TC-07 · Check Disk (with punctuation)

**Type:** `check disk!`

**Expected response:** Same as TC-04

**Pass if:** Punctuation is ignored; same disk response appears.

---

### TC-08 · Check Disk (uppercase)

**Type:** `CHECK DISK`

**Expected response:** Same as TC-04

**Pass if:** Uppercase is handled; same disk response appears.

---

## Section 3 — Memory Monitoring

---

### TC-09 · Check Memory (exact command)

**Type:** `check memory`

**Expected response:**
```
Memory: XX.X% used (X,XXX MB / X,XXX MB) — OK
```

**Pass if:** Response contains `Memory:`, a percentage, `MB`, and a status.

---

### TC-10 · Check Memory (natural language)

**Type:** `how much ram am i using`

**Expected response:** Same structure as TC-09

**Pass if:** Response contains `Memory:` and a percentage.

---

### TC-11 · Check Memory (alternate keyword)

**Type:** `check ram`

**Expected response:** Same structure as TC-09

**Pass if:** Response contains `Memory:` and a percentage.

---

## Section 4 — CPU Monitoring

---

### TC-12 · Check CPU (exact command)

**Type:** `check cpu`

**Expected response:**
```
CPU: XX.X% used (X logical cores) — OK
```

**Pass if:** Response contains `CPU:`, a percentage, `logical cores`, and a status.

---

### TC-13 · Check CPU (natural language)

**Type:** `whats my cpu load`

**Expected response:** Same structure as TC-12

**Pass if:** Response contains `CPU:` and `cores`.

---

### TC-14 · Check CPU (alternate phrasing)

**Type:** `cpu usage`

**Expected response:** Same structure as TC-12

**Pass if:** Response contains `CPU:` and a percentage.

---

## Section 5 — Uptime

---

### TC-15 · Check Uptime (exact command)

**Type:** `check uptime`

**Expected response:**
```
Uptime: Xd Xh Xm
```
*(e.g. `Uptime: 6d 2h 45m`)*

**Pass if:** Response contains `Uptime:` followed by days, hours, and minutes.

---

### TC-16 · Check Uptime (natural language)

**Type:** `how long has the server been up`

**Expected response:** Same as TC-15

**Pass if:** Response contains `Uptime:` and time values.

---

### TC-17 · Check Uptime (alternate phrasing)

**Type:** `server uptime`

**Expected response:** Same as TC-15

**Pass if:** Response contains `Uptime:`.

---

## Section 6 — Open Ports

---

### TC-18 · Check Ports (exact command)

**Type:** `check ports`

**Expected response:**
```
Open ports: 22, 53, 80, 8001, ...
```
*(exact ports depend on what is running on the server)*

**Pass if:** Response contains `Open ports:` followed by at least one port number.

---

### TC-19 · Check Ports (natural language)

**Type:** `what ports are open`

**Expected response:** Same as TC-18

**Pass if:** Response contains `Open ports:`.

---

### TC-20 · Check Ports (alternate phrasing)

**Type:** `listening ports`

**Expected response:** Same as TC-18

**Pass if:** Response contains `Open ports:`.

---

## Section 7 — Process Monitoring

---

### TC-21 · Top Processes (exact command)

**Type:** `top processes`

**Expected response:**
```
Top 5 processes by CPU:
  [1234] python — CPU 5.0% | MEM 1.23%
  [5678] nginx  — CPU 0.5% | MEM 0.45%
  ...
```

**Pass if:** Response contains `Top 5 processes` and at least one line with `CPU` and `MEM` values.

---

### TC-22 · Top Processes (natural language)

**Type:** `what processes are hogging memory`

**Expected response:** Same structure as TC-21

**Pass if:** Response contains `Top 5 processes` — NOT a memory usage report.

---

### TC-23 · Top Processes (alternate phrasing)

**Type:** `show running processes`

**Expected response:** Same structure as TC-21

**Pass if:** Response contains `processes` and CPU/MEM values.

---

## Section 8 — System Health Summary

---

### TC-24 · System Health (exact command)

**Type:** `system health`

**Expected response:**
```
System Health — Overall: OK
  Disk:   OK (XX.X%)
  Memory: OK (XX.X%)
  CPU:    OK (XX.X%)
  Uptime: Xd Xh Xm
```
*(Status values may be WARNING or CRITICAL depending on actual usage)*

**Pass if:** Response contains all four lines: `Disk:`, `Memory:`, `CPU:`, `Uptime:`, plus `Overall:`.

---

### TC-25 · System Health (natural language)

**Type:** `show me the system status`

**Expected response:** Same as TC-24

**Pass if:** Response contains `Overall:`, `Disk:`, `Memory:`, `CPU:`.

---

### TC-26 · System Health — Critical Highlight

**Type:** `system health`

**Expected response:** Same structure as TC-24

**Pass if:** If any metric shows `CRITICAL`, the chat bubble background turns light red.
If any metric shows `WARNING`, the bubble turns light yellow.
If all OK, bubble is normal gray.

---

## Section 9 — Log Analysis

---

### TC-27 · Log Analysis — HIGH Severity (DB error)

Two methods are supported — try both.

**Method A — Type inline:**
```
analyze logs: ERROR db connection failed ERROR db connection failed ERROR db connection failed ERROR db connection failed
```

**Expected response (Method A):**
```
Log Analysis → Severity: HIGH | Root cause: Database connectivity issue | Impact: Critical | Actions: Review error logs, Inspect database connectivity/queries
```

**Method B — Upload a log file:**
1. Create a file called `test_db.log` on your Windows machine with this content:
   ```
   ERROR db connection failed
   ERROR db connection failed
   ERROR db connection failed
   ERROR db connection failed
   ```
2. Click the **📎 Upload Log** button next to the chat input
3. Select `test_db.log` from the file browser

**Expected response (Method B):**
```
Log File: test_db.log
Severity: HIGH | Root cause: Database connectivity issue | Impact: Critical
Actions: Review error logs, Inspect database connectivity/queries
```

The button shows `Analysing…` while the file is being processed, then resets to `📎 Upload Log`.

**Pass if:** Either method returns a response containing `Severity: HIGH` and `Database`.

---

### TC-28 · Log Analysis — MEDIUM Severity (warnings)

**Type:**
```
analyze logs: WARNING slow response time WARNING high memory usage INFO startup complete
```

**Expected response:**
```
Log Analysis → Severity: MEDIUM | Root cause: Unclear root cause... | ...
```

**Pass if:** Response contains `Severity: MEDIUM`.

---

### TC-29 · Log Analysis — LOW Severity

**Type:**
```
analyze logs: INFO service started INFO health check passed INFO request completed
```

**Expected response:**
```
Log Analysis → Severity: LOW | ...
```

**Pass if:** Response contains `Severity: LOW`.

---

### TC-30 · Log Analysis — Timeout Root Cause

**Type:**
```
analyze logs: ERROR TIMEOUT waiting for database response ERROR TIMEOUT connecting to service
```

**Expected response:**
```
Log Analysis → Severity: HIGH | Root cause: Network timeout detected | ...
```

**Pass if:** Response contains `timeout` in root cause.

---

### TC-31 · Log Analysis — Auth Root Cause

**Type:**
```
analyze logs: ERROR AUTH token expired ERROR AUTH invalid credentials
```

**Expected response:**
```
Log Analysis → Severity: HIGH | Root cause: Authentication failure detected | ...
```

**Pass if:** Response contains `Authentication` in root cause.

---

### TC-32 · Log Analysis — Missing Content

**Type:** `analyze logs:`

**Expected response:**
```
Usage: analyze logs: <paste log content here>
```

**Pass if:** Response shows usage hint (not an error crash).

---

## Section 10 — Alerts

---

### TC-33 · Show Alerts via Chat

**Type:** `show alerts`

**Expected response (if no alerts yet):**
```
No alerts recorded yet.
```

**Expected response (if alerts exist):**
```
Recent alerts (X unacknowledged):
  [!] [WARNING] Disk WARNING: 85.0% used  (2026-05-02 21:04:05)
  [✓] [INFO]    Test alert  (2026-05-02 21:00:00)
```

**Pass if:** Response contains `alert` — either `No alerts` or a list with severity tags.

---

### TC-34 · Alerts Tab — View Alert List

**Action:** Click the **Alerts** tab in the navigation bar

**Expected:** Alerts panel appears showing a list of alert cards.
Each card shows: severity badge (CRITICAL / WARNING / INFO), message text, timestamp, and an **Ack** button.

**Pass if:** Alerts tab opens and shows either "No alerts to show." or a list of alert cards.

---

### TC-35 · Alerts Tab — Acknowledge an Alert

**Prerequisite:** At least one unacknowledged alert is visible in the Alerts tab

**Action:** Click the **Ack** button on any alert card

**Expected:** The Ack button is replaced by a green `✓ Acked` label. The unacknowledged count badge in the nav bar decreases by 1.

**Pass if:** Alert switches to acked state without page reload.

---

### TC-36 · Alerts Tab — Filter Unacknowledged

**Action:** In the Alerts tab, click the **Unacknowledged** filter button

**Expected:** Only alerts with `!` (unacked) status are shown. Acked alerts are hidden.

**Pass if:** All visible alert cards do not show `✓ Acked`.

---

### TC-37 · Alerts Tab — Filter Critical

**Action:** Click the **Critical** filter button

**Expected:** Only alerts with red `CRITICAL` badge are shown.

**Pass if:** No WARNING or INFO badges are visible (or "No alerts to show." if none exist).

---

## Section 11 — Runbooks

---

### TC-38 · List Available Runbooks

**Type:** `list runbooks`

**Expected response:**
```
Available runbooks:
  run clear_tmp — Delete files in /tmp older than 1 day
  run disk_breakdown — Show disk usage of top-level directories
  run large_logs — List log files over 50MB in /var/log
  run listening_services — List all listening services with PIDs
```

**Pass if:** Response lists all 4 runbooks with their descriptions.

---

### TC-39 · Runbook — Request (shows confirmation prompt)

**Type:** `run clear_tmp`

**Expected response:**
```
Runbook: Delete files in /tmp older than 1 day
Command: find /tmp -maxdepth 1 -mtime +1 -delete

Reply 'confirm clear_tmp' to execute, or 'cancel' to abort.
```

**Pass if:** Response shows the runbook description, command preview, and confirmation instructions.

---

### TC-40 · Runbook — Cancel After Request

**Prerequisite:** TC-39 was just executed (confirm prompt is shown)

**Type:** `cancel`

**Expected response:**
```
Cancelled.
```

**Pass if:** Response says `Cancelled.`

---

### TC-41 · Runbook — Confirm After Cancel Should Fail

**Prerequisite:** TC-39 and TC-40 were just executed

**Type:** `confirm clear_tmp`

**Expected response:**
```
No pending confirmation for 'clear_tmp'. Use 'run clear_tmp' first.
```

**Pass if:** Response shows an error (cancellation was respected).

---

### TC-42 · Runbook — Full Execute Flow

**Step 1 — Type:** `run listening_services`

**Expected:** Confirmation prompt appears:
```
Runbook: List all listening services with PIDs
Command: ss -tlnp

Reply 'confirm listening_services' to execute, or 'cancel' to abort.
```

**Step 2 — Type:** `confirm listening_services`

**Expected response:**
```
Runbook executed.

State   Recv-Q  Send-Q  Local Address:Port ...
LISTEN  0       128     0.0.0.0:22  ...
...
```

**Pass if:** Step 1 shows the confirmation prompt. Step 2 shows `Runbook executed.` followed by actual command output.

---

### TC-43 · Runbook — Unknown Runbook Name

**Type:** `run nonexistent_job`

**Expected response:**
```
Unknown runbook 'nonexistent_job'. Available: clear_tmp, disk_breakdown, large_logs, listening_services
```

**Pass if:** Response says unknown and lists available runbook names.

---

### TC-44 · Runbook — Confirm Without Prior Request

**Type:** `confirm clear_tmp`
*(without first typing `run clear_tmp`)*

**Expected response:**
```
No pending confirmation for 'clear_tmp'. Use 'run clear_tmp' first.
```

**Pass if:** Response shows an error — runbook did NOT execute.

---

### TC-45 · Runbook — Wrong Confirm Name

**Step 1 — Type:** `run clear_tmp`

**Step 2 — Type:** `confirm disk_breakdown`
*(wrong name)*

**Expected response for Step 2:**
```
No pending confirmation for 'disk_breakdown'. Use 'run disk_breakdown' first.
```

**Pass if:** Step 2 shows an error and clear_tmp did NOT execute.

---

## Section 12 — Configuration

---

### TC-46 · View Current Config via Chat

**Type:** `config`

**Expected response:**
```
Current thresholds:
  disk_warning: 80.0
  disk_critical: 90.0
  memory_warning: 80.0
  memory_critical: 90.0
  cpu_warning: 70.0
  cpu_critical: 85.0
  health_check_interval: 60
```

**Pass if:** Response lists all 7 threshold keys with their current values.

---

### TC-47 · Config Tab — View Settings Form

**Action:** Click the **Config** tab in the navigation bar

**Expected:** A settings form appears with labeled number inputs for:
- Disk Warning % / Critical %
- Memory Warning % / Critical %
- CPU Warning % / Critical %
- Health Check Interval (seconds)

**Pass if:** All 7 input fields are visible and populated with current values.

---

### TC-48 · Config Tab — Save New Threshold

**Action:**
1. Click the **Config** tab
2. Change **Disk Warning** from `80` to `75`
3. Click **Save Settings**

**Expected:** A `Settings saved.` message appears briefly below the button.

**Step 2 — Verify:** Go back to Chat tab and type `config`

**Expected response:**
```
Current thresholds:
  disk_warning: 75.0
  ...
```

**Pass if:** `disk_warning` shows `75.0` and all other values are unchanged.

---

## Section 13 — Metrics Tab

---

### TC-49 · Metrics Tab — Charts Load

**Action:** Click the **Metrics** tab

**Expected:**
- Three summary tiles appear showing current Disk %, Memory %, CPU %
- Three line charts appear below: Disk Usage %, Memory Usage %, CPU Usage %
- Charts may show flat or no data if the server just started

**Pass if:** All three chart panels are visible. No JavaScript errors in browser console.

---

### TC-50 · Metrics Tab — Refresh Button

**Action:**
1. Click the **Metrics** tab
2. Click the **Refresh** button

**Expected:** Summary tiles and charts update with the latest values.

**Pass if:** Values refresh without page reload. Charts show updated data points.

---

## Section 14 — Chat History

---

### TC-51 · Chat History Persists on Reload

**Step 1 — Type:** `check disk`
*(wait for response)*

**Step 2 — Reload the browser page (F5)**

**Expected:** Previous messages (`check disk` and its response) reappear in the chat window automatically.

**Pass if:** Chat history is visible after page reload.

---

### TC-52 · Clear Chat History

**Action:** Click the **Clear** button next to the chat input

**Expected:** All chat bubbles are removed. A confirmation message appears:
```
Chat history cleared.
```

**Step 2 — Reload the browser page (F5)**

**Expected after reload:** Chat window is empty (only the cleared message or welcome).

**Pass if:** History is cleared from both the UI and the database.

---

## Section 15 — Run Tests via Chat

---

### TC-53 · Run All Tests via Chat

**Type:** `run tests`

**Expected response:**
```
Test Run — ALL PASSED

..............................................................................
.........................
97 passed in X.XXs
```

**Pass if:** Response contains `ALL PASSED` and `97 passed`. *(Test run may take 10-20 seconds to respond — this is normal.)*

---

### TC-54 · Run Tests (alternate phrasing)

**Type:** `run test suite`

**Expected response:** Same as TC-53

**Pass if:** Response contains `ALL PASSED`.

---

### TC-55 · Run Tests (pytest keyword)

**Type:** `pytest`

**Expected response:** Same as TC-53

**Pass if:** Response contains `ALL PASSED`.

---

## Section 16 — Edge Cases & Error Handling

---

### TC-56 · Unknown Command

**Type:** `xyzzy nonsense blah`

**Expected response:**
```
I didn't understand that. Try: check disk, check memory, check cpu, top processes, system health, or type 'help' for all commands.
```

**Pass if:** Response contains "didn't understand" or similar fallback message. Does NOT crash or show a server error.

---

### TC-57 · Special Characters in Input

**Type:** `check disk; rm -rf /`

**Expected response:** Same as `check disk` — the special characters are stripped safely.

**Pass if:** Response shows disk info. The dangerous characters are ignored (sanitized).

---

### TC-58 · Very Long Input

**Type:** Type or paste 500+ random characters (e.g. repeat `abcdefg` many times)

**Expected response:**
```
I didn't understand that. Try: check disk...
```

**Pass if:** App responds gracefully without crashing or timing out.

---

### TC-59 · Enter Key Sends Message

**Type:** `check memory` *(press Enter instead of clicking Send)*

**Expected:** Message is sent; Memory response appears.

**Pass if:** Enter key works as a substitute for the Send button.

---

### TC-60 · Alert Badge Updates Automatically

**Action:**
1. Stay on the Chat tab
2. Wait up to 60 seconds (the background health check interval)

**Expected:** If any metric (disk, memory, CPU) crosses a threshold, the **Alerts** tab badge (red circle with a number) appears or increments automatically without refreshing the page.

**Pass if:** Badge updates without manual refresh. *(This may not trigger if all metrics are below thresholds — that is also a PASS.)*

---

## Test Execution Tracker

Copy this table to track your results:

| TC # | Description | Result | Notes |
|------|-------------|--------|-------|
| TC-01 | Welcome message on load | | |
| TC-02 | Help command | | |
| TC-03 | Empty message → help | | |
| TC-04 | Check disk — exact | | |
| TC-05 | Check disk — natural language | | |
| TC-06 | Check disk — alternate phrasing | | |
| TC-07 | Check disk — with punctuation | | |
| TC-08 | Check disk — uppercase | | |
| TC-09 | Check memory — exact | | |
| TC-10 | Check memory — natural language | | |
| TC-11 | Check memory — ram keyword | | |
| TC-12 | Check CPU — exact | | |
| TC-13 | Check CPU — natural language | | |
| TC-14 | Check CPU — alternate phrasing | | |
| TC-15 | Check uptime — exact | | |
| TC-16 | Check uptime — natural language | | |
| TC-17 | Check uptime — alternate | | |
| TC-18 | Check ports — exact | | |
| TC-19 | Check ports — natural language | | |
| TC-20 | Check ports — alternate | | |
| TC-21 | Top processes — exact | | |
| TC-22 | Top processes — natural language | | |
| TC-23 | Top processes — alternate | | |
| TC-24 | System health — exact | | |
| TC-25 | System health — natural language | | |
| TC-26 | System health — color coding | | |
| TC-27 | Log analysis — HIGH / DB | | |
| TC-28 | Log analysis — MEDIUM / warnings | | |
| TC-29 | Log analysis — LOW | | |
| TC-30 | Log analysis — timeout root cause | | |
| TC-31 | Log analysis — auth root cause | | |
| TC-32 | Log analysis — missing content | | |
| TC-33 | Show alerts via chat | | |
| TC-34 | Alerts tab — view list | | |
| TC-35 | Alerts tab — acknowledge | | |
| TC-36 | Alerts tab — filter unacked | | |
| TC-37 | Alerts tab — filter critical | | |
| TC-38 | List runbooks | | |
| TC-39 | Runbook — request prompt | | |
| TC-40 | Runbook — cancel | | |
| TC-41 | Runbook — confirm after cancel fails | | |
| TC-42 | Runbook — full execute flow | | |
| TC-43 | Runbook — unknown name | | |
| TC-44 | Runbook — confirm without request | | |
| TC-45 | Runbook — wrong confirm name | | |
| TC-46 | Config via chat | | |
| TC-47 | Config tab — view form | | |
| TC-48 | Config tab — save threshold | | |
| TC-49 | Metrics tab — charts load | | |
| TC-50 | Metrics tab — refresh | | |
| TC-51 | Chat history — persists on reload | | |
| TC-52 | Chat history — clear | | |
| TC-53 | Run tests via chat | | |
| TC-54 | Run tests — alternate phrasing | | |
| TC-55 | Run tests — pytest keyword | | |
| TC-56 | Unknown command fallback | | |
| TC-57 | Special characters sanitized | | |
| TC-58 | Very long input handled | | |
| TC-59 | Enter key sends message | | |
| TC-60 | Alert badge auto-updates | | |

---

**Total: 60 test cases**
- Chat message tests: TC-01 to TC-33, TC-38 to TC-46, TC-53 to TC-60
- UI interaction tests: TC-34 to TC-37, TC-47 to TC-52
