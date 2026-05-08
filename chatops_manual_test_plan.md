# ChatOps Manual Test Plan — Browser Execution Guide

## Setup

1. Open your browser on Windows
2. Navigate to the ChatOps URL (e.g. `http://<server-ip>:8001/chatops`)
3. A **Sign In** overlay appears — log in with the default credentials:
   - Username: `admin`  |  Password: `admin`
4. After login the main console appears with a blue header and tab navigation
5. Type each message exactly as shown and compare the response

> **Default credentials:** `admin` / `admin` — change the password after first login using `add user` to create a new admin account and `remove user admin` to deactivate the default.
> **Session:** Your login session lasts 8 hours. After it expires, the login page reappears automatically.

**How to mark results:**
- ✅ PASS — response matches the expected output
- ❌ FAIL — response is missing expected content or shows an error

**Note:** Values like percentages, port numbers, process names, and timestamps
will differ on your machine — focus on the **keywords and structure**, not exact numbers.

---

## Section 1 — Help & Welcome

---

### TC-01 · Login Page & Header Bar

**Action:** Open the chatbot URL in the browser (no typing needed)

**Step 1 — Before login:**
A centered white card overlay appears on a grey background with:
- Title: "ChatOps Console"
- Subtitle: "Sign in to access the operations dashboard"
- Username and Password input fields
- **Sign In** button

The blue header and all tabs are hidden until login succeeds.

**Step 2 — After logging in with `admin` / `admin`:**

The overlay disappears and the blue header bar shows:
```
ChatOps Console
disk · memory · cpu · health · ports · type help for all commands
```
The hint text appears as a small subtitle. The word **help** appears slightly brighter.
In the top-right corner of the header: username **admin**, a small **admin** role badge, and a **Sign Out** button.

If you have previously used the chatbot, old messages reappear in the chat window below a
`— previous session —` divider. The chat window itself has NO automatic welcome bubble.

**Pass if:**
- Login overlay appears before main app
- After correct credentials: overlay hides, header visible with username and role badge
- Hint text visible in the blue header
- Chat window opens at the last message with `— previous session —` divider

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

**Type:** `show system config`  *(also accepted: `config`)*

**Expected response:**
```
System Configuration

Disk Thresholds:
  Warning:   80.0%
  Critical:  90.0%

Memory Thresholds:
  Warning:   80.0%
  Critical:  90.0%

CPU Thresholds:
  Warning:   70.0%
  Critical:  85.0%

Health Check:
  Interval:  60s

Slack:
  Webhook:   (not configured)
  Suppress:  10 minutes

Daily Report:
  Status:    Disabled
  Hour:      08:00
```

**Pass if:** Response shows all grouped sections — Disk/Memory/CPU thresholds, Health Check, Slack, and Daily Report.

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

> **Note:** The `run tests`, `run test suite`, and `pytest` commands are intentionally hidden from the Help tab and chat help output. They are for internal QA use only and are not part of the end-user interface.

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

---

## Section 17 — Network Monitoring

---

### TC-61 · Check IP Addresses

**Type:** `check ip`

**Expected response:**
```
Network interfaces:
  lo           UNKNOWN    127.0.0.1/8
  eth0         UP         10.0.0.1/24 ...
```

**Pass if:** Response lists at least one interface with a state and IP address.

---

### TC-62 · Check Routes

**Type:** `check routes`

**Expected response:**
```
Routing table:
  default via 10.0.0.1 dev eth0
  10.0.0.0/24 dev eth0 proto kernel ...
```

**Pass if:** Response contains "Routing table" and at least one route entry.

---

### TC-63 · Check Network Stats

**Type:** `check network`

**Expected response:**
```
Network interface stats:
  lo           RX: 0.5 MB   TX: 0.5 MB   Err in/out: 0/0   Drop in/out: 0/0
  eth0         RX: 120.3 MB TX: 45.1 MB  Err in/out: 0/0   Drop in/out: 0/0
```

**Pass if:** Response contains at least one interface with RX/TX values.

---

### TC-64 · Check DNS

**Type:** `check dns`

**Expected response:**
```
DNS: google.com → 142.250.x.x  Latency: 12.4ms  Status: OK
```

**Pass if:** Response contains "DNS", a resolved IP, and `Status: OK`.

---

### TC-65 · Check Connections

**Type:** `check connections`

**Expected response:**
```
TCP connections: 8 total  (ESTAB: 5  TIME-WAIT: 3)
```

**Pass if:** Response contains "connections" and a total count.

---

## Section 18 — Service Management

---

### TC-66 · Service Status — Known Service

**Type:** `service status ssh`

**Expected response:**
```
Service: ssh
  Status: active (running)
  PID: 1234
  OpenBSD Secure Shell server
```

**Pass if:** Response contains "Service: ssh" and a status line.

---

### TC-67 · Service Status — Unknown Service

**Type:** `service status fakeservice`

**Expected response:**
```
Service: fakeservice
  Status: inactive (dead)
```

**Pass if:** Response contains "Service: fakeservice" and does not crash.

---

### TC-68 · Restart Service — Confirmation Prompt

**Type:** `restart ssh`

**Expected response:**
```
Restart service 'ssh'?
Command: systemctl restart ssh

Reply 'confirm restart ssh' to proceed, or 'cancel' to abort.
```

**Pass if:** Response contains "confirm restart ssh" and "cancel".

---

### TC-69 · Restart Service — Cancel

**Type:** `restart ssh` then `cancel`

**Expected:** Second response contains "Cancelled."

**Pass if:** Cancel clears the pending restart.

---

### TC-70 · Restart Service — Confirm Without Prior Request

**Type:** `confirm restart nginx` (without first typing `restart nginx`)

**Expected response:**
```
No pending restart for 'nginx'. Use 'restart nginx' first.
```

**Pass if:** Response contains "No pending restart".

---

### TC-71 · Check Failed Services

**Type:** `check failed services`

**Expected response (if none failed):**
```
No failed services detected.
```

**Expected response (if any failed):**
```
Failed services:
  nginx
  myapp
```

**Pass if:** Response contains either "No failed services" or a list of service names.

---

## Section 19 — Multi-instance Support

---

### TC-72 · Add a Node

**Type:** `add node web-01 ubuntu@192.168.1.10`

**Expected response:**
```
Node 'web-01' added — ubuntu@192.168.1.10  (key: ~/.ssh/id_rsa)
```

**Pass if:** Response confirms node was added with correct user and host.

---

### TC-73 · List Nodes — With Nodes Registered

**Type:** `list nodes` (after TC-72)

**Expected response:**
```
Registered nodes:
  web-01 — ubuntu@192.168.1.10  (key: ~/.ssh/id_rsa)
```

**Pass if:** Response shows the registered node.

---

### TC-74 · List Nodes — Empty Registry

**Type:** `list nodes` (with no nodes added)

**Expected response:**
```
No nodes registered.
Usage: add node <name> <user>@<host> [key_path]
```

**Pass if:** Response contains "No nodes registered".

---

### TC-75 · Remove a Node

**Type:** `remove node web-01` (after TC-72)

**Expected response:**
```
Node 'web-01' removed.
```

**Pass if:** Node no longer appears in `list nodes`.

---

### TC-76 · Remove Non-existent Node

**Type:** `remove node ghost`

**Expected response:**
```
Node 'ghost' not found.
```

**Pass if:** Response contains "not found".

---

### TC-77 · Remote Command — Specific Node

**Prerequisite:** A real reachable node registered (e.g., `add node local ubuntu@127.0.0.1`)

**Type:** `check disk on local`

**Expected response:**
```
[local]  ubuntu@127.0.0.1
  Total: 50G | Used: 20G | Free: 28G | Usage: 42%
```

**Pass if:** Response contains the node name and disk usage data.

---

### TC-78 · Remote Command — All Nodes

**Prerequisite:** At least two nodes registered

**Type:** `system health on all`

**Expected response:**
```
Remote: system health — all nodes

[web-01]  ubuntu@192.168.1.10
  Disk: 45%
  Memory: 62%
  ...
```

**Pass if:** Response shows output for each registered node.

---

### TC-79 · Remote Command — Unknown Node

**Type:** `check disk on unknown-host`

**Expected response:**
```
Unknown node 'unknown-host'. Available: web-01, db-server
```

**Pass if:** Response contains "Unknown node" and lists available nodes.

---

## Section 20 — Slack Alert Notifications

---

### TC-80 · Configure Slack Webhook via Chat

**Type:** `config set slack_webhook https://hooks.slack.com/services/test/url`

**Expected response:**
```
Slack webhook configured. CRITICAL alerts will be sent to Slack.
```

**Pass if:** Response confirms webhook was saved.

---

### TC-81 · Test Slack — No Webhook Configured

**Type:** `test slack` (before configuring a webhook)

**Expected response:**
```
No Slack webhook configured. Use: config set slack_webhook <url>
```

**Pass if:** Response contains "No Slack webhook configured".

---

### TC-82 · Test Slack — Webhook Configured

**Prerequisite:** A valid Slack webhook URL configured (TC-80)

**Type:** `test slack`

**Expected response:**
```
Test notification sent to Slack.
```

**Pass if:** Response confirms success AND a test message appears in the Slack channel.

---

### TC-83 · Set Alert Suppression Window

**Type:** `config set alert suppress 15`

**Expected response:**
```
Alert suppression set to 15 minutes.
```

**Pass if:** Response confirms the new suppression window.

---

### TC-84 · CRITICAL Alert Triggers Slack Notification

**Prerequisite:** Valid Slack webhook configured; lower a threshold below current usage (e.g., set `cpu_critical` to 5%)

**Action:** Wait up to 60 seconds for the next health check cycle.

**Expected:** A Slack message appears in the configured channel:
```
🚨 [CRITICAL] ChatOps Alert
  Cpu: XX.X% used
  Host: `<hostname>`  |  2026-05-03 09:14:00
```

**Pass if:** Slack message received with correct metric and severity.

---

### TC-85 · Slack Alert Suppression

**Prerequisite:** TC-84 just fired a Slack notification

**Action:** Wait for the next health check (within the suppression window).

**Expected:** No second Slack notification sent within the suppression period.

**Pass if:** Only one notification per suppression window per metric.

---

### TC-86 · Config Tab — Slack Settings Visible

**Action:** Open Config tab in the browser.

**Expected:** New fields visible:
- Slack Webhook URL text input
- Alert Suppression (minutes) number input

**Pass if:** Both fields are present and save correctly via the Save Settings button.

---

## Section 21 — Daily Health Reports

---

### TC-87 · Show Report — Default 24h

**Type:** `show report`

**Expected response:**
```
Health Report — Last 24h  (2026-05-03 09:30:00)
Host: web-01

  Disk     avg: 61.2%  min: 60.8%  max: 74.0%  (96 samples)
  Memory   avg: 71.4%  min: 68.1%  max: 89.0%  (96 samples)
  Cpu      avg: 34.1%  min: 2.0%   max: 88.0%  (96 samples)

  Alerts: 3 total  (1 unacknowledged)  ⚠
```

**Pass if:** Response contains "Health Report", hostname, metric stats, and alert count.

---

### TC-88 · Show Report — Custom Time Window

**Type:** `show report 48h`

**Expected response:**
```
Health Report — Last 48h  (...)
```

**Pass if:** Response header says "Last 48h".

---

### TC-89 · Enable Daily Report

**Type:** `config set report on`

**Expected response:**
```
Daily report enabled.
```

**Pass if:** Response contains "enabled".

---

### TC-90 · Disable Daily Report

**Type:** `config set report off`

**Expected response:**
```
Daily report disabled.
```

**Pass if:** Response contains "disabled".

---

### TC-91 · Set Report Hour

**Type:** `config set report hour 9`

**Expected response:**
```
Daily report scheduled for 09:00 each day.
```

**Pass if:** Response confirms the scheduled hour.

---

### TC-92 · Config Tab — Daily Report Section

**Action:** Open Config tab in the browser.

**Expected:** New Daily Report section visible with:
- Enabled On/Off dropdown
- Hour (0–23) number input
- Both fields save correctly via Save Settings

**Pass if:** Both fields present and values persist after save.

---

### TC-93 · Report API Endpoint

**Action:** Navigate to `http://<server>:8001/chatops/report` in browser (or use curl)

**Expected JSON response:**
```json
{
  "hostname": "web-01",
  "hours": 24,
  "generated_at": "2026-05-03 09:30:00",
  "metrics": {
    "disk":   {"avg": 61.2, "min": 60.8, "max": 74.0, "samples": 96},
    "memory": {"avg": 71.4, "min": 68.1, "max": 89.0, "samples": 96},
    "cpu":    {"avg": 34.1, "min": 2.0,  "max": 88.0, "samples": 96}
  },
  "alerts": {"total": 3, "unacked": 1}
}
```

**Pass if:** Response contains all required keys with numeric values.

---

## Test Execution Tracker (Phase 2)

| TC # | Description | Result | Notes |
|------|-------------|--------|-------|
| TC-61 | Check IP addresses | | |
| TC-62 | Check routes | | |
| TC-63 | Check network stats | | |
| TC-64 | Check DNS | | |
| TC-65 | Check connections | | |
| TC-66 | Service status — known | | |
| TC-67 | Service status — unknown | | |
| TC-68 | Restart — confirmation prompt | | |
| TC-69 | Restart — cancel | | |
| TC-70 | Confirm restart without request | | |
| TC-71 | Check failed services | | |
| TC-72 | Add node | | |
| TC-73 | List nodes — populated | | |
| TC-74 | List nodes — empty | | |
| TC-75 | Remove node | | |
| TC-76 | Remove non-existent node | | |
| TC-77 | Remote command — single node | | |
| TC-78 | Remote command — all nodes | | |
| TC-79 | Remote command — unknown node | | |
| TC-80 | Config Slack webhook via chat | | |
| TC-81 | Test slack — no webhook | | |
| TC-82 | Test slack — valid webhook | | |
| TC-83 | Set alert suppression | | |
| TC-84 | CRITICAL alert fires Slack | | |
| TC-85 | Alert suppression prevents re-fire | | |
| TC-86 | Config tab — Slack fields | | |
| TC-87 | Show report — 24h | | |
| TC-88 | Show report — custom window | | |
| TC-89 | Enable daily report | | |
| TC-90 | Disable daily report | | |
| TC-91 | Set report hour | | |
| TC-92 | Config tab — report section | | |
| TC-93 | Report API endpoint | | |

---

**Phase 2 Total: 33 new test cases (TC-61 to TC-93)**
- Network monitoring: TC-61 to TC-65
- Service management: TC-66 to TC-71
- Multi-instance: TC-72 to TC-79
- Slack notifications: TC-80 to TC-86
- Daily reports: TC-87 to TC-93

---

## Section 22 — Login & Authentication

---

### TC-94 · Login Overlay Appears Before App

**Action:** Open the ChatOps URL with no stored session (use a fresh browser / incognito window)

**Expected:**
- White login card centred on grey background
- Title: "ChatOps Console"
- Subtitle: "Sign in to access the operations dashboard"
- Username and Password fields
- **Sign In** button
- Blue header, nav tabs, and chat window are NOT visible yet

**Pass if:** Login card is the first and only thing visible on the page.

---

### TC-95 · Login — Wrong Password

**Action:** Enter username `admin`, password `wrongpassword`, click **Sign In**

**Expected:** Error message appears in red below the button:
```
Invalid username or password.
```
The login overlay stays open. The main app does not appear.

**Pass if:** Error is shown inline; app remains hidden.

---

### TC-96 · Login — Blank Fields

**Action:** Leave both fields empty and click **Sign In**

**Expected:**
```
Enter username and password.
```

**Pass if:** Validation fires before sending a request to the server.

---

### TC-97 · Login — Correct Credentials

**Action:** Enter `admin` / `admin`, click **Sign In** (or press Enter in the password field)

**Expected:**
- Login overlay disappears
- Blue header becomes visible
- Top-right of header shows: username `admin` · role badge `admin` · **Sign Out** button
- Chat tab is active; previous session history loads

**Pass if:** All of the above are visible after login.

---

### TC-98 · Enter Key Works on Login Form

**Action:** Type `admin` in username, press **Tab**, type `admin` in password, press **Enter**

**Expected:** Login proceeds exactly as clicking the Sign In button.

**Pass if:** Enter key in the password field submits the form.

---

### TC-99 · Session Persists on Page Reload

**Prerequisite:** Successfully logged in (TC-97)

**Action:** Reload the page (F5 or browser refresh)

**Expected:**
- Login overlay does NOT appear
- App loads directly with main interface
- Username and role badge still visible in header

**Pass if:** No re-login required after reload within the 8-hour session window.

---

### TC-100 · Sign Out

**Action:** Click the **Sign Out** button in the header

**Expected:**
- Login overlay reappears immediately
- Main app (header + tabs + chat) is hidden again
- After page reload, login overlay still appears (token cleared)

**Pass if:** Sign Out clears the session and restores the login page.

---

### TC-101 · API Requires Authentication

**Action:**
1. Sign out (TC-100)
2. Open browser developer tools (F12) → Console tab
3. Type: `fetch('/chatops/config').then(r => console.log(r.status))`

**Expected:** Console prints `401`

**Pass if:** Unauthenticated API access returns 401, not 200.

---

## Section 23 — User Management

> **Prerequisite for all tests in this section:** Logged in as `admin`.

---

### TC-102 · Add a New User via Chat

**Type:** `add user john abc123 operator`

**Expected:**
```
User 'john' created with role 'operator'.
```

**Pass if:** Response confirms user was created with the correct role.

---

### TC-103 · List Users via Chat

**Type:** `list users`

**Expected:**
```
Users:
  admin — admin (active)
  john  — operator (active)
```

**Pass if:** Both users appear with role and status.

---

### TC-104 · New User Can Log In

**Prerequisite:** TC-102 completed

**Action:** Sign out, then log in with username `john` / password `abc123`

**Expected:**
- Login succeeds
- Header shows username `john` · role badge `operator`

**Pass if:** New user account works immediately after creation.

---

### TC-105 · Operator Role — Cannot Change Config

**Prerequisite:** Logged in as `john` (operator)

**Action:** Go to the Config tab and click **Save Settings**

**Expected:** Request fails with a permission error (browser console shows 403).
The `show system config` chat command still works (read-only).

**Pass if:** Operator can read config but PUT request returns 403.

---

### TC-106 · Set User Role via Chat

**Prerequisite:** Logged in as `admin`

**Type:** `set role john viewer`

**Expected:**
```
User 'john' role updated to 'viewer'.
```

**Pass if:** Role updated. Log in as `john` and verify role badge shows `viewer`.

---

### TC-107 · Deactivate User via Chat

**Prerequisite:** Logged in as `admin`

**Type:** `remove user john`

**Expected:**
```
User 'john' deactivated.
```

**Pass if:** Response confirms deactivation.

---

### TC-108 · Deactivated User Cannot Log In

**Prerequisite:** TC-107 completed

**Action:** Sign out, try to log in as `john` / `abc123`

**Expected:** "Invalid username or password." error (deactivated accounts are blocked)

**Pass if:** Login is rejected for deactivated user.

---

### TC-109 · Duplicate Username Shows Error

**Type:** `add user admin newpass123 viewer`

**Expected:**
```
User 'admin' already exists.
```

**Pass if:** No duplicate created; error returned.

---

### TC-110 · Invalid Role Shows Error via Chat

**Type:** `add user dave pass123 superuser`

*(superuser is not a valid role)*

**Expected:** The command does not match the pattern (requires `viewer`, `operator`, or `admin`) — router returns the "I didn't understand" fallback.

**Pass if:** No user is created; fallback message shown.

---

## Section 24 — Audit Trail

> **Prerequisite:** Logged in as `admin`.

---

### TC-111 · Audit Log Records Commands

**Step 1 — Send a command:** `check disk`

**Step 2 — Type:** `show audit log`

**Expected:**
```
Recent audit log (last 10):
  [2026-05-04 22:15] admin: check disk
  [2026-05-04 22:14] admin: show audit log
  ...
```

**Pass if:** "check disk" appears in the audit log attributed to `admin`.

---

### TC-112 · Audit Log Shows Multiple Users

**Prerequisite:** Create user `john` (TC-102), log in as `john`, send `check memory`, log back in as `admin`

**Type:** `show audit log`

**Expected:** Log shows entries from both `admin` and `john` with their respective commands.

**Pass if:** Both usernames appear in the audit log.

---

### TC-113 · Audit API — Requires Authentication

**Action:**
1. Sign out
2. Open browser console and type:
   `fetch('/chatops/audit').then(r => console.log(r.status))`

**Expected:** Console prints `401`

**Pass if:** Audit endpoint is not accessible without login.

---

## Section 25 — Docker Deployment

> **Prerequisite:** Docker and Docker Compose installed on the host machine.

---

### TC-114 · Build Docker Image

**Action:** On the server, run:
```bash
cd /home/<user>/chatops
docker build -t chatops .
```

**Expected:** Build completes without errors. Final line shows the image tag.

**Pass if:** `docker images chatops` shows the image with a recent timestamp.

---

### TC-115 · Start with Docker Compose

**Action:**
```bash
docker-compose up -d
```

Then open `http://<server>:8000/chatops` in a browser.

**Expected:** ChatOps login page appears. Log in with `admin` / `admin`.

**Pass if:** App loads and login succeeds through the Docker container.

---

### TC-116 · Data Persists After Container Restart

**Prerequisite:** TC-115 running; send 3 chat messages

**Action:**
```bash
docker-compose restart
```
Wait ~5 seconds, then reload the browser and log in.

**Expected:** Previous chat messages reappear under `— previous session —`.

**Pass if:** SQLite data persisted in the Docker volume across restart.

---

### TC-117 · Custom Secret Key via Environment Variable

**Action:** In `docker-compose.yml`, set `CHATOPS_SECRET=my-custom-secret` and restart.
Log in. Reload the page.

**Expected:** Session token signed with the new secret — existing tokens are invalidated (login page reappears after restart, which is expected and correct).

**Pass if:** App starts successfully and accepts new logins after secret change.

---

## Test Execution Tracker (Phase 3 — Auth, Users, Audit, Docker)

| TC # | Description | Result | Notes |
|------|-------------|--------|-------|
| TC-94  | Login overlay before app | | |
| TC-95  | Login — wrong password error | | |
| TC-96  | Login — blank fields validation | | |
| TC-97  | Login — correct credentials | | |
| TC-98  | Enter key on login form | | |
| TC-99  | Session persists on reload | | |
| TC-100 | Sign Out clears session | | |
| TC-101 | API returns 401 without auth | | |
| TC-102 | Add user via chat | | |
| TC-103 | List users via chat | | |
| TC-104 | New user can log in | | |
| TC-105 | Operator cannot change config | | |
| TC-106 | Set user role | | |
| TC-107 | Deactivate user via chat | | |
| TC-108 | Deactivated user cannot log in | | |
| TC-109 | Duplicate username error | | |
| TC-110 | Invalid role not accepted | | |
| TC-111 | Audit log records commands | | |
| TC-112 | Audit log shows multiple users | | |
| TC-113 | Audit API requires auth | | |
| TC-114 | Build Docker image | | |
| TC-115 | Start with docker-compose | | |
| TC-116 | Data persists after restart | | |
| TC-117 | Custom secret key via env var | | |

---

**Phase 3 Total: 24 new test cases (TC-94 to TC-117)**
- Login & authentication: TC-94 to TC-101
- User management: TC-102 to TC-110
- Audit trail: TC-111 to TC-113
- Docker deployment: TC-114 to TC-117

**Phase 3 Grand total: 117 manual test cases**

---

## Section 26 — LLM / AI Integration

> **Prerequisite for all tests in this section:** Logged in as `admin`.
> The LLM provider defaults to `none` (disabled) on a fresh install. Tests are grouped by provider so you can run only the providers you have access to.

---

### TC-118 · Config Display Includes LLM Section

**Type:** `show system config`

**Expected response includes (near the bottom):**
```
LLM / AI:
  Provider:  none
  Model:     -
  API Key:   (not set)
  Ollama URL:http://localhost:11434
```

**Pass if:** Response contains an `LLM / AI:` section with all four rows: Provider, Model, API Key, and Ollama URL.

---

### TC-119 · Help Command Lists LLM Commands

**Type:** `help`

**Expected response includes:**
```
AI / LLM:
  explain alert <id> | test llm
  config set llm provider <ollama|groq|claude|none>
  config set llm api key <key> | config set llm model <model>
  config set ollama url <url>
```

**Pass if:** Help output contains the `AI / LLM:` section with `explain alert`, `test llm`, and the four `config set llm` commands.

---

### TC-120 · Set LLM Provider — Valid Value

**Type:** `config set llm provider ollama`

**Expected:**
```
LLM provider set to 'ollama'.
```

**Verify:** Type `show system config` — the Provider row now shows `ollama` and Model shows `llama3.2` (auto-selected default).

**Pass if:** Provider is saved and reflected in config display.

---

### TC-121 · Set LLM Provider — Invalid Value

**Type:** `config set llm provider openai`

**Expected:**
```
Unknown provider 'openai'. Choose: none, ollama, groq, claude
```

**Pass if:** Error message is shown; provider is unchanged (type `show system config` to confirm).

---

### TC-122 · Set LLM Provider — Disable (none)

**Prerequisite:** Provider currently set to any value (e.g., from TC-120)

**Type:** `config set llm provider none`

**Expected:**
```
LLM provider set to 'none'.
```

**Pass if:** Provider resets to `none`. Running `test llm` immediately after returns the "not configured" guidance message.

---

### TC-123 · Set LLM API Key

**Type:** `config set llm api key gsk_testkey12345`

**Expected:**
```
LLM API key saved.
```

**Verify:** Type `show system config` — the API Key row shows `******2345` (last 4 characters visible, rest masked with `*`).

**Pass if:** Key is saved; masked format shown in config — full key is NOT printed back.

---

### TC-124 · Set LLM Model Override (with dot in name)

**Type:** `config set llm model llama3.2`

**Expected:**
```
LLM model set to 'llama3.2'.
```

**Verify:** Type `show system config` — Model row shows `llama3.2` (dot preserved).

**Pass if:** Model name including the `.` character is saved exactly as typed. This verifies the dot is not stripped.

---

### TC-125 · Set Ollama URL

**Type:** `config set ollama url http://192.168.1.5:11434`

**Expected:**
```
Ollama URL set to 'http://192.168.1.5:11434'.
```

**Verify:** Type `show system config` — Ollama URL row shows the new address.

**Pass if:** Custom URL is saved and displayed in config.

**Reset after test:** `config set ollama url http://localhost:11434` to restore the default.

---

### TC-126 · test llm — Provider Not Configured

**Prerequisite:** `config set llm provider none`

**Type:** `test llm`

**Expected:**
```
LLM not configured. Use:
  config set llm provider <ollama|groq|claude>
  config set llm api key <key>  (groq/claude only)
```

**Pass if:** Guidance message is shown. No crash, no server error, no blank response.

---

### TC-127 · test llm — Cloud Provider Without API Key

**Step 1 — Type:** `config set llm provider groq`

**Step 2 — Type:** `test llm` *(without setting an API key)*

**Expected:**
```
LLM not configured. Use:
  config set llm provider <ollama|groq|claude>
  config set llm api key <key>  (groq/claude only)
```

**Pass if:** Missing API key is caught before any outbound network call. Guidance message shown.

---

### TC-128 · test llm — Ollama (Local, Free)

> **Prerequisite:** Ollama installed and running (`ollama serve`), `llama3.2` model pulled (`ollama pull llama3.2`).

**Step 1 — Type:** `config set llm provider ollama`

**Step 2 — Type:** `test llm`

**Expected:**
```
LLM test: LLM OK
```
*(Exact wording may vary — the model may rephrase, but a short response is returned)*

**Pass if:** Response contains `LLM test:` followed by a non-empty, non-error string. Error bracket format like `[Ollama unreachable:...]` must NOT appear.

---

### TC-129 · test llm — Groq (Cloud, Free Tier)

> **Prerequisite:** A free Groq API key from `console.groq.com`.

**Step 1 — Type:** `config set llm provider groq`

**Step 2 — Type:** `config set llm api key <your-groq-key>`

**Step 3 — Type:** `test llm`

**Expected:**
```
LLM test: LLM OK
```

**Pass if:** Response contains `LLM test:` and no error bracket. Confirms the Groq API key and endpoint are working.

---

### TC-130 · test llm — Claude (Anthropic API)

> **Prerequisite:** A valid Anthropic API key.

**Step 1 — Type:** `config set llm provider claude`

**Step 2 — Type:** `config set llm api key <your-anthropic-key>`

**Step 3 — Type:** `config set llm model claude-haiku-4-5-20251001`

**Step 4 — Type:** `test llm`

**Expected:**
```
LLM test: LLM OK
```

**Pass if:** Response contains `LLM test:` and no error bracket. Confirms Claude Haiku API connectivity.

---

### TC-131 · explain alert — LLM Not Configured

**Prerequisite:** `config set llm provider none`

**Step 1 — Type:** `show alerts` to note any existing alert ID (e.g., `3`)

**Step 2 — Type:** `explain alert 3`

**Expected:**
```
LLM not configured. Use: config set llm provider <ollama|groq|claude>
```

**Pass if:** Guidance message shown with no crash or blank response. The alert itself is NOT modified.

---

### TC-132 · explain alert — Valid Alert, LLM Active

> **Prerequisite:** LLM configured and connectivity confirmed (TC-128, TC-129, or TC-130 passed).

**Step 1 — Type:** `show alerts`

Note an alert ID from the list (e.g., `5`).

**Step 2 — Type:** `explain alert 5`

**Expected structure:**
```
Alert #5 — WARNING
Disk WARNING: 85.2% used

RCA:
<2–3 sentence plain-English root cause and recommended action>
```

**Pass if:**
- The original alert message is shown at the top
- An `RCA:` section is present with a non-empty response
- No error bracket appears in the RCA text (e.g., `[Groq HTTP 401...]` would be a FAIL)
- Response arrives within 15 seconds

---

### TC-133 · explain alert — Non-existent Alert ID

> **Prerequisite:** LLM configured

**Type:** `explain alert 99999`

**Expected:**
```
Alert #99999 not found.
```

**Pass if:** Clean "not found" message returned. No LLM call is made (response is instant). No server error or crash.

---

## Test Execution Tracker (Phase 4 — LLM / AI Integration)

| TC # | Description | Result | Notes |
|------|-------------|--------|-------|
| TC-118 | Config display includes LLM section | | |
| TC-119 | Help lists LLM commands | | |
| TC-120 | Set LLM provider — valid | | |
| TC-121 | Set LLM provider — invalid value | | |
| TC-122 | Set LLM provider — disable (none) | | |
| TC-123 | Set LLM API key — masked in display | | |
| TC-124 | Set LLM model — dot preserved | | |
| TC-125 | Set Ollama URL | | |
| TC-126 | test llm — provider not set | | |
| TC-127 | test llm — cloud provider, no key | | |
| TC-128 | test llm — Ollama (local) | | |
| TC-129 | test llm — Groq (free tier) | | |
| TC-130 | test llm — Claude (Anthropic) | | |
| TC-131 | explain alert — LLM not configured | | |
| TC-132 | explain alert — valid alert, RCA returned | | |
| TC-133 | explain alert — non-existent ID | | |

---

**Phase 4 Total: 16 new test cases (TC-118 to TC-133)**
- Config & setup: TC-118 to TC-125
- Provider connectivity: TC-126 to TC-130
- RCA / explain alert: TC-131 to TC-133

**Grand total: 133 manual test cases**
