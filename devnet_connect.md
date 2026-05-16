# DevNet Cat8kv — Connection & Test Runbook

## Prerequisites
- WSL2 + Ubuntu installed
- OpenConnect installed in Ubuntu (`sudo apt install openconnect`)
- ChatOps app at `C:\deepak\Chatops\Chatopscode`
- DevNet sandbox active (check: https://developer.cisco.com/site/sandbox)

---

## Step 1 — Start Ubuntu WSL2 Terminal

Open a terminal in VS Code or from Start menu → search "Ubuntu"

---

## Step 2 — Connect DevNet VPN (Ubuntu terminal)

```bash
sudo openconnect --protocol=anyconnect devnetsandbox-usw1-reservation.cisco.com:20175
```

**When prompted:**
- GROUP: leave as `SSLClient` (just press Enter)
- Username: *(your DevNet VPN username from Quick Access tab)*
- Password: *(your DevNet VPN password from Quick Access tab)*

**Success looks like:**
```
CSTP connected. DPD 30, Keepalive 20
Established DTLS connection ...
Configured as 192.168.254.x ...
```

**Keep this terminal open** — closing it disconnects the VPN.

---

## Step 3 — Enable IP Forwarding + NAT (Ubuntu terminal, new tab)

Open a second Ubuntu terminal tab and run:

```bash
echo 1 | sudo tee /proc/sys/net/ipv4/ip_forward
sudo iptables -t nat -A POSTROUTING -o tun0 -j MASQUERADE
```

---

## Step 4 — Add Windows Route (PowerShell as Administrator)

```powershell
route ADD 10.10.20.0 MASK 255.255.255.0 172.17.127.221
```

> Note: WSL2 IP is usually `172.17.127.221`. Verify with `wsl hostname -I` if it changed.

---

## Step 5 — Verify Windows Can Reach Cat8kv

```powershell
Test-NetConnection -ComputerName 10.10.20.48 -Port 22
```

**Expected:** `TcpTestSucceeded : True`

If False — recheck VPN is connected in Ubuntu and route was added.

---

## Step 6 — Start ChatOps App (PowerShell)

```powershell
cd C:\deepak\Chatops\Chatopscode
.\venv\Scripts\Activate.ps1
uvicorn app:app --reload --host 0.0.0.0 --port 8001
```

Wait for: `Uvicorn running on http://0.0.0.0:8001`

---

## Step 7 — Get Auth Token (new PowerShell window)

```powershell
cd C:\deepak\Chatops\Chatopscode
.\get_token.ps1
```

**Expected:** `Token set: eyJhbGciOiJI...`

---

## Step 8 — Run Network Tests

```powershell
.\network_tests.ps1
```

**Expected output sections:**
- DEVICE INFO — hostname: cat8000v, version: 17.12.02
- INTERFACES — GigabitEthernet1 up, others admin down
- ROUTING TABLE — default route via 10.10.20.254
- BGP NEIGHBORS — no BGP (expected, not configured)
- CPU & MEMORY — utilization percentages
- ARP TABLE — 10.10.20.50 and 10.10.20.254 entries

All sections completing without errors = connectivity confirmed.

---

## Sandbox Device Reference

> **These IPs and credentials are fixed for every reservation of the "IOS XE on Cat8kv" blueprint.**
> You do NOT need to re-register devices in ChatOps after a new reservation — they stay valid.
> Only the VPN username/password changes — check the Quick Access tab each time.

| Device      | IP           | Port | Username  | Password    | ChatOps Name | Type       |
|-------------|--------------|------|-----------|-------------|--------------|------------|
| Cat8kv      | 10.10.20.48  | 22   | developer | C1sco12345  | cat8kv       | cisco_xe   |
| Cat8kv      | 10.10.20.48  | 830  | developer | C1sco12345  | —            | NETCONF    |
| IOS-XRv 9K  | 10.10.20.35  | 22   | developer | C1sco12345  | ios-xrv      | cisco_xr   |
| Nexus 9K    | 10.10.20.40  | 22   | admin     | RG!_Yw200   | nexus9k      | cisco_nxos |
| DevBox      | 10.10.20.50  | 22   | developer | C1sco12345  | devbox       | linux      |

**What changes each reservation:**
- VPN username and password (always check Quick Access tab)

**What stays the same:**
- All device IPs (10.10.20.x)
- All device SSH credentials
- VPN host: `devnetsandbox-usw1-reservation.cisco.com:20175`
- ChatOps device registrations (no need to re-register)

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| VPN auth fails | Check Quick Access tab for correct username/password |
| `TcpTestSucceeded: False` | Re-run Step 3 (iptables) and Step 4 (route) |
| `Unable to connect` on ChatOps | App not running — repeat Step 6 |
| Token empty | Re-run `.\get_token.ps1` |
| CPU shows `unknown` | Fixed in network.py — restart uvicorn |
| Sandbox expired | Reserve a new one at developer.cisco.com/sandbox |
