   Activate it
  .\venv\Scripts\Activate.ps1

  # Install all dependencies
  pip install -r requirements.txt

  After that, to run the app:
  uvicorn app:app --reload --host 0.0.0.0 --port 8000



$token = (Invoke-RestMethod -Method POST -Uri "http://localhost:8001/chatops/auth/login" -ContentType
  "application/json" -Body '{"username":"admin","password":"admin"}').access_token

  Then register the Cat8kv:

  $body = '{"name":"cat8kv","host":"10.10.20.48","port":22,"username":"developer","password":"C1sco12345","device_type":
  "cisco_xe"}'
  Invoke-RestMethod -Method POST -Uri "http://localhost:8001/chatops/network/devices" -ContentType "application/json"
  -Headers @{ Authorization = "Bearer $token" } -Body $body

  Then test connectivity to the device:

  Invoke-RestMethod -Method GET -Uri "http://localhost:8001/chatops/network/devices/cat8kv/info" -Headers @{
  Authorization = "Bearer $token" }




The Cat8kv sandbox is ready. Here's the exact sequence to get connected and test:

  Step 1 — Get sandbox credentials

  On the DevNet sandbox page (Operation Hub > IOS XE on Cat8kv), look for:
  - VPN credentials (host, username, password) — needed for AnyConnect
  - Device IP (usually 10.10.20.x range)
  - SSH credentials (usually developer / C1sco12345)

  The page should show a "Details" or "Access" tab with all of this.

  Step 2 — Connect AnyConnect VPN

  Download Cisco AnyConnect from the sandbox page if you don't have it, then:
  1. Open AnyConnect
  2. Enter the VPN host from the sandbox page
  3. Login with the VPN username/password shown on the page

  Step 3 — Re-login to get a fresh token (if needed)

  $token = (Invoke-RestMethod -Method POST -Uri "http://localhost:8001/chatops/auth/login" -ContentType "application/json" -Body
  '{"username":"admin","password":"admin"}').access_token

  Step 4 — Delete the old devnet-csr entry

  Invoke-RestMethod -Method DELETE -Uri "http://localhost:8001/chatops/network/devices/devnet-csr" -Headers @{ Authorization = "Bearer $token" }

  Step 5 — Register the Cat8kv device

  Replace <DEVICE_IP> with the IP shown on the sandbox page:

  $body = '{"name":"cat8kv","host":"<DEVICE_IP>","port":22,"username":"developer","password":"C1sco12345","device_type":"cisco_xe"}'
  Invoke-RestMethod -Method POST -Uri "http://localhost:8001/chatops/network/devices" -ContentType "application/json" -Headers @{ Authorization = "Bearer
  $token" } -Body $body

  Step 6 — First connectivity test

  Invoke-RestMethod -Method GET -Uri "http://localhost:8001/chatops/network/devices/cat8kv/info" -Headers @{ Authorization = "Bearer $token" }

  Share the sandbox "Access" tab details (IP, VPN host) and I'll give you the exact commands with real values filled in.




 ---
  1. Create a free Cisco DevNet account
  - Go to the URL you already have: https://devnetsandbox.cisco.com
  - Click Log In → Sign Up if you don't have an account
  - Use any email — it's completely free

  ---
  2. Find and reserve the IOS-XE sandbox
  - After login, search for "IOS XE on CSR" or "IOS XE programmability"
  - Click the sandbox → click Reserve
  - Choose duration (up to 4 hours, extendable)
  - You'll get an email when it's ready (usually 5–10 minutes)

  ---
  3. Connect via VPN
  The reservation email includes:
  - VPN host, username, and password
  - Connect using Cisco AnyConnect (free download) or OpenConnect

  Once VPN is connected, the sandbox device is reachable on its private IP — no firewall issues.

  ---
  4. Update your device in ChatOps

  # Delete the existing entry
  Invoke-RestMethod -Method DELETE -Uri "http://localhost:8001/chatops/network/devices/devnet-csr" -Headers @{ Authorization = "Bearer $token" }


  # Re-add with the reserved sandbox IP/credentials from your email
  Invoke-RestMethod -Method POST -Uri "http://localhost:8001/chatops/network/devices" -ContentType "application/json" -Headers @{ Authorization = "Bearer
  $token" } -Body '{"name":"devnet-csr","host":"<IP_FROM_EMAIL>","username":"<USER_FROM_EMAIL>","password":"<PASS_FROM_EMAIL>","device_type":"cisco_xe","port":
  22,"netconf_port":830,"description":"Reserved DevNet IOS-XE"}'

  ---

  ▎ The reserved sandbox gives you a real Cisco CSR1000v with full SSH + NETCONF access — much more reliable than the always-on shared one.


 Yes, the Cat8kv (Catalyst 8000v) runs IOS-XE, so it's fully compatible with the ChatOps network module. Here's what to expect:

  ---
  Will work out of the box (same device_type: cisco_xe):
  - show version → device info
  - show ip interface brief + show interfaces → interface status
  - show ip route → routing table
  - show arp → ARP table
  - show running-config → config backup
  - show processes cpu / show processes memory → CPU/memory
  - Config push via send_config_set
  - NETCONF on port 830

  ---
  Register it in ChatOps after VPN connects:

  Invoke-RestMethod -Method POST -Uri "http://localhost:8001/chatops/network/devices" `
    -ContentType "application/json" `
    -Headers @{ Authorization = "Bearer $token" } `
    -Body '{"name":"cat8kv","host":"<IP_FROM_RESERVATION>","username":"<USERNAME>","password":"<PASSWORD>","device_type":"cisco_xe","port":22,"netconf_port":83
  0,"description":"DevNet Cat8kv IOS-XE"}'

  ---
  One thing to note: Cat8kv is a newer platform than CSR1000v — some show command output formats may differ slightly (e.g. show version header), but the regex
  parsers in network.py handle both. If any field comes back as "unknown", that just means the parser didn't match that specific line — the raw output will
  still be there.

  Go ahead and reserve it — it's a better sandbox than the always-on CSR for hands-on testing.







  # Create the virtual environment
  /

  # Activate it
  .\venv\Scripts\Activate.ps1

  # Install all dependencies
  pip install -r requirements.txt

  After that, to run the app:
  uvicorn app:app --reload --host 0.0.0.0 --port 8000

  ▎ Note: If PowerShell blocks the activation script, run this once first to allow it:
  ▎ Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

  The venv folder will appear in C:\Deepak\Chatops\Chatopscode\venv\. It's already in .gitignore so it won't be committed.



# ChatOps — Network Feature Test Plan

**Audience:** Developer / Operator learning the networking features  
**Scope:** All network device management features — REST API, chat commands, and background polling  
**Prerequisite:** App running at `http://localhost:8000` (see "How to run" section)  
**Test device:** Cisco DevNet Always-On IOS-XE sandbox — publicly available, no VPN needed

---

## DevNet Sandbox Credentials (Cisco Always-On)

| Field         | Value                                        |
|---------------|----------------------------------------------|
| Host          | `sandbox-iosxe-latest-1.cisco.com`           |
| SSH Port      | `22`                                         |
| NETCONF Port  | `830`                                        |
| Username      | `developer`                                  |
| Password      | `C1sco12345`                                 |
| Device Type   | `cisco_xe`                                   |

> These are Cisco's public always-on sandboxes. They may change — check https://devnetsandbox.cisco.com if connection fails.

---


bearer  - eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc3ODkyMzk3OX0.C3b8qwR7vWKOz1jAGWNUrejfHCcgiV1rfflI7M9gYUY
## How to Run the App

```powershell
cd C:\Deepak\Chatops\Chatopscode
pip install -r requirements.txt
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

Open browser: **http://localhost:8000/chatops**  
Login: `admin` / `admin`


 Start-Job -ScriptBlock { cd C:\Deepak\Chatops\Chatopscode; .\venv\Scripts\Activate.ps1; uvicorn app:app --reload --host 0.0.0.0 --port 8001 }

  Useful commands after that:

  # Check if it's running
  Get-Job

  # See the uvicorn logs
  Receive-Job 1

  # Stop it
  Stop-Job 1
  Remove-Job 1

  Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd 'C:\Deepak\Chatops\Chatopscode'; .\venv\Scripts\Activate.ps1; uvicorn app:app --reload
  --host 0.0.0.0 --port 8000"


This is the actual command for bearer token:
$token = (Invoke-RestMethod -Method POST -Uri "http://localhost:8001/chatops/auth/login" -ContentType "application/json" -Body '{"username": "admin","password": "admin"}').token

bearer token  - eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsInJvbGUiOiJhZG1pbiIsImV4cCI6MTc3ODkyMzk3OX0.C3b8qwR7vWKOz1jAGWNUrejfHCcgiV1rfflI7M9gYUY

---

## Getting an Auth Token (for API tests)

All REST endpoints require a Bearer token. Get one first:

```bash
curl -X POST http://localhost:8000/chatops/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin"}'
```

Response:
```json
{"token": "<YOUR_TOKEN>", "username": "admin", "role": "admin"}
```


Save the token — use it as `Authorization: Bearer <YOUR_TOKEN>` in all requests below.

---

## Section 1 — Register a Network Device

### 1.1 Add a DevNet device
**What it does:** Registers a network device in the DB. Password is base64-obfuscated at rest.


This is the actual command for Powershell:
 Invoke-RestMethod -Method POST -Uri "http://localhost:8001/chatops/network/devices" -ContentType "application/json" -Headers @{ Authorization = "Bearer
  $token" } -Body '{"name":"devnet-csr","host":"sandbox-iosxe-latest-1.cisco.com","username":"developer","password":"C1sco12345","device_type":"cisco_xe","port  ":22,"netconf_port":830,"description":"Cisco DevNet Always-On IOS-XE"}'

  Expected response:
  id          : 1
  name        : devnet-csr
  host        : sandbox-iosxe-latest-1.cisco.com
  device_type : cisco_xe

  Then test the connection by fetching device info (runs show version via SSH):
  Invoke-RestMethod -Uri "http://localhost:8001/chatops/network/devices/devnet-csr/info" -Headers @{ Authorization = "Bearer $token" }


 If TcpTestSucceeded: False — your network blocks outbound SSH. Try the alternative DevNet sandbox that uses port 8022:

  # Delete the existing device first
  Invoke-RestMethod -Method DELETE -Uri "http://localhost:8001/chatops/network/devices/devnet-csr" -Headers @{ Authorization = "Bearer $token" }

  # Re-add with port 8022
  Invoke-RestMethod -Method POST -Uri "http://localhost:8001/chatops/network/devices" -ContentType "application/json" -Headers @{ Authorization = "Bearer
  $token" } -Body '{"name":"devnet-csr","host":"sandbox-iosxe-latest-1.cisco.com","username":"developer","password":"C1sco12345","device_type":"cisco_xe","port
  ":8022,"netconf_port":10000,"description":"Cisco DevNet Always-On IOS-XE"}'

  If TcpTestSucceeded: True — sandbox is reachable but credentials changed. Check the current credentials at
  https://devnetsandbox.cisco.com/DevNet/catalog/always-on-iosxe.











**What it does:** Registers a network device in the DB. Password is base64-obfuscated at rest.

**REST:**
```bash
curl -X POST http://localhost:8000/chatops/network/devices \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "name":         "devnet-csr",
    "host":         "sandbox-iosxe-latest-1.cisco.com",
    "username":     "developer",
    "password":     "C1sco12345",
    "device_type":  "cisco_xe",
    "port":         22,
    "netconf_port": 830,
    "description":  "Cisco DevNet Always-On IOS-XE"
  }'
```

**Expected response:**
```json
{"id": 1, "name": "devnet-csr", "host": "sandbox-iosxe-latest-1.cisco.com", "device_type": "cisco_xe"}
```

**UI:** Go to the **Network** tab → click **Add Device** → fill in the form.

---

### 1.2 List registered devices

```bash
curl http://localhost:8000/chatops/network/devices \
  -H "Authorization: Bearer <TOKEN>"
```

**Expected:** Array containing `devnet-csr` with host, device_type, description.

---

### 1.3 Duplicate name is rejected

```bash
curl -X POST http://localhost:8000/chatops/network/devices \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name":"devnet-csr","host":"1.2.3.4","username":"x","password":"y","device_type":"cisco_xe"}'
```

**Expected:** `409 Conflict` — "Device name already exists"

---

## Section 2 — Device Info (show version)

**What it does:** SSH into the device and runs `show version`. Returns hostname, IOS version, model, uptime, serial.

```bash
curl http://localhost:8000/chatops/network/devices/devnet-csr/info \
  -H "Authorization: Bearer <TOKEN>"
```

**Expected response shape:**
```json
{
  "status": "ok",
  "hostname": "CSR1000V",
  "version": "17.x.x",
  "uptime": "X days, X hours...",
  "model": "CSR1000V",
  "serial": "9XXXXX",
  "raw": "..."
}
```

**What to look for:**
- `status` must be `"ok"` — if `"error"`, the device is unreachable or credentials are wrong
- `version` confirms IOS-XE
- `raw` shows the first 800 chars of the actual CLI output

---

## Section 3 — Interface Status

**What it does:** Runs `show ip interface brief` + `show interfaces`. Returns each interface with IP, status, protocol, input/output rates, and error counters.

```bash
curl http://localhost:8000/chatops/network/devices/devnet-csr/interfaces \
  -H "Authorization: Bearer <TOKEN>"
```

**Expected response shape:**
```json
{
  "status": "ok",
  "interfaces": [
    {
      "interface": "GigabitEthernet1",
      "ip": "10.10.20.48",
      "status": "up",
      "protocol": "up",
      "in_rate": 1000,
      "out_rate": 500,
      "errors_in": 0,
      "errors_out": 0
    }
  ]
}
```

**What to look for:**
- `status: up / protocol: up` = healthy
- `status: down` or `protocol: down` = problem — the background poller will create a WARNING alert for this
- Error counters incrementing = data-plane issues

**Side effect:** This call also writes to `network_interface_log` table (for history tracking).

---

## Section 4 — Routing Table

**What it does:** Runs `show ip route`. Returns structured routes with code, network, distance, metric, and next-hop.

```bash
curl http://localhost:8000/chatops/network/devices/devnet-csr/routes \
  -H "Authorization: Bearer <TOKEN>"
```

**Expected response shape:**
```json
{
  "status": "ok",
  "routes": [
    {"code": "C", "network": "10.10.20.0/24", "distance": "0", "metric": "0", "next_hop": "..."},
    {"code": "S", "network": "0.0.0.0/0", "distance": "1", "metric": "0", "next_hop": "..."}
  ],
  "raw": "..."
}
```

**Route codes to know:**
| Code | Meaning            |
|------|--------------------|
| C    | Connected          |
| S    | Static             |
| O    | OSPF               |
| B    | BGP                |
| L    | Local              |

---

## Section 5 — BGP Neighbors

**What it does:** Runs `show bgp summary` (falls back to `show ip bgp summary`). Returns each neighbor with AS number, state, and prefix count.

```bash
curl http://localhost:8000/chatops/network/devices/devnet-csr/bgp \
  -H "Authorization: Bearer <TOKEN>"
```

**Expected response:**
```json
{
  "status": "ok",
  "neighbors": [
    {"neighbor": "10.0.0.1", "as": "65001", "state": "Established", "prefixes": "5", "updown": "1d02h"}
  ],
  "raw": "..."
}
```

> On the DevNet sandbox, BGP may not be configured — `neighbors` will be an empty array. That's normal.

---

## Section 6 — CPU & Memory Utilization

**What it does:** Runs `show processes cpu sorted` and `show processes memory sorted`. Returns CPU % and raw memory bytes.

```bash
curl http://localhost:8000/chatops/network/devices/devnet-csr/cpu \
  -H "Authorization: Bearer <TOKEN>"
```

**Expected:**
```json
{
  "status": "ok",
  "cpu_5sec": "3",
  "mem_used_bytes": "345678912",
  "mem_free_bytes": "234567890",
  "cpu_raw": "...",
  "mem_raw": "..."
}
```

---

## Section 7 — ARP Table

**What it does:** Runs `show arp`. Returns IP-to-MAC mappings with interface.

```bash
curl http://localhost:8000/chatops/network/devices/devnet-csr/arp \
  -H "Authorization: Bearer <TOKEN>"
```

**Expected:**
```json
{
  "status": "ok",
  "entries": [
    {"ip": "10.10.20.254", "mac": "0000.0c9f.f4d2", "interface": "GigabitEthernet1"}
  ],
  "raw": "..."
}
```

---

## Section 8 — Config Backup

**What it does:** Runs `show running-config`, strips blank lines, stores it in `network_config_backups` table. Returns `backup_id` and line count.

### 8.1 Take a backup

```bash
curl -X POST http://localhost:8000/chatops/network/devices/devnet-csr/backup \
  -H "Authorization: Bearer <TOKEN>"
```

**Expected:**
```json
{"backup_id": 1, "device": "devnet-csr", "lines": 87}
```

**Also logged in audit trail** — visible in `show audit log` or `GET /chatops/audit`.

### 8.2 List all backups for a device

```bash
curl http://localhost:8000/chatops/network/devices/devnet-csr/backups \
  -H "Authorization: Bearer <TOKEN>"
```

### 8.3 Get the latest backup

```bash
curl http://localhost:8000/chatops/network/devices/devnet-csr/backups/latest \
  -H "Authorization: Bearer <TOKEN>"
```

**Expected:** Full config text, line count, and timestamp.

---

## Section 9 — Push Config (Config Mode)

**What it does:** Enters config mode and applies a list of CLI commands. Saves config after. Requires `admin` role.

> **Warning:** This modifies the device. Only use on DevNet sandboxes or devices you control.

```bash
curl -X POST http://localhost:8000/chatops/network/devices/devnet-csr/push-config \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"commands": ["interface Loopback99", "description Test from ChatOps", "no shutdown"]}'
```

**Expected:**
```json
{"status": "ok", "output": "...config mode output..."}
```

**Verify it worked:**
```bash
# Check interfaces — Loopback99 should now appear
curl http://localhost:8000/chatops/network/devices/devnet-csr/interfaces \
  -H "Authorization: Bearer <TOKEN>"
```

**Clean up (restore):**
```bash
curl -X POST http://localhost:8000/chatops/network/devices/devnet-csr/push-config \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"commands": ["no interface Loopback99"]}'
```

---

## Section 10 — Delete a Device

**What it does:** Removes the device record. Requires `admin` role.

```bash
curl -X DELETE http://localhost:8000/chatops/network/devices/devnet-csr \
  -H "Authorization: Bearer <TOKEN>"
```

**Expected:** `{"deleted": "devnet-csr"}`

After deletion, re-add it if you want to continue testing.

---

## Section 11 — Background Network Poller

**What it does:** Every `health_check_interval` seconds (default: 60s), the app automatically polls all registered devices. If an interface is `down` or the device is unreachable, it creates an alert.

### 11.1 Verify alerts are generated

After the app has been running for ~60s with `devnet-csr` registered:

```bash
curl "http://localhost:8000/chatops/alerts?limit=20" \
  -H "Authorization: Bearer <TOKEN>"
```

Look for alerts with `source: "devnet-csr"`.

**In the UI:** Go to the **Alerts** tab — network alerts appear alongside system alerts.

### 11.2 Acknowledge a network alert

```bash
curl -X POST http://localhost:8000/chatops/alerts/1/ack \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Section 12 — Error Scenarios

These tests confirm the app handles failures gracefully.

| Test | How to trigger | Expected |
|------|----------------|----------|
| Wrong credentials | Add device with bad password, call `/info` | `{"status": "error", "error": "Authentication failed..."}` |
| Unreachable host | Add device with IP `1.2.3.4`, call `/interfaces` | `{"status": "error", "error": "TCP connection...timed out"}` |
| Device not found | Call `/info` for a name that doesn't exist | `404 Device not found` |
| Push config without admin | Use operator token to call `/push-config` | `403 Insufficient permissions` |
| Duplicate device name | Add same name twice | `409 Conflict` |

---

## Section 13 — UI Walkthrough (Network Tab)

In the browser at **http://localhost:8000/chatops**, go to the **Network** tab:

| UI Element | What it does |
|---|---|
| Add Device form | Registers a new network device |
| Device list | Shows all registered devices |
| Info button | Calls `/info` — shows version, model, uptime |
| Interfaces button | Opens interface status modal |
| Routes button | Shows routing table |
| BGP button | Shows BGP neighbor summary |
| CPU button | Shows CPU/memory utilization |
| Backup button | Triggers config backup |
| ARP button | Shows ARP table |
| Delete button | Removes the device |

---

## Section 14 — Audit Trail Verification

Every network action is logged. After running the tests above:

```bash
curl "http://localhost:8000/chatops/audit?limit=20" \
  -H "Authorization: Bearer <TOKEN>"
```

**Or in chat:**
```
show audit log
```

**Expected entries:**
- `network device add devnet-csr sandbox-iosxe-latest-1.cisco.com`
- `network backup devnet-csr`
- `network push-config devnet-csr: 3 commands`
- `network device remove devnet-csr`

---

## Quick Reference — All Network Endpoints

| Method | Endpoint | Role Required | Description |
|--------|----------|---------------|-------------|
| GET | `/chatops/network/devices` | viewer | List all devices |
| POST | `/chatops/network/devices` | operator | Register a device |
| DELETE | `/chatops/network/devices/{name}` | admin | Remove a device |
| GET | `/chatops/network/devices/{name}/info` | viewer | `show version` |
| GET | `/chatops/network/devices/{name}/interfaces` | viewer | Interface status |
| GET | `/chatops/network/devices/{name}/routes` | viewer | Routing table |
| GET | `/chatops/network/devices/{name}/bgp` | viewer | BGP neighbors |
| GET | `/chatops/network/devices/{name}/cpu` | viewer | CPU/memory |
| GET | `/chatops/network/devices/{name}/arp` | viewer | ARP table |
| POST | `/chatops/network/devices/{name}/backup` | operator | Pull running-config |
| GET | `/chatops/network/devices/{name}/backups` | viewer | List backups |
| GET | `/chatops/network/devices/{name}/backups/latest` | viewer | Latest backup |
| POST | `/chatops/network/devices/{name}/push-config` | admin | Push CLI commands |

---

*Test plan generated: 2026-05-15 | Project: ChatOps Console v0.1*
