# DevNet Sandbox — Connection & ChatOps Runbook

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

## Step 5 — Verify Connectivity

```powershell
Test-NetConnection -ComputerName 10.10.20.48 -Port 22   # Cat8kv
Test-NetConnection -ComputerName 10.10.20.35 -Port 22   # IOS-XRv
Test-NetConnection -ComputerName 10.10.20.40 -Port 22   # Nexus 9K
Test-NetConnection -ComputerName 10.10.20.50 -Port 22   # DevBox
```

**Expected:** `TcpTestSucceeded : True` for all four.

If False — recheck VPN is connected in Ubuntu and route was added.

---

## Step 6 — Fix IOS-XRv SSH Key (required each new reservation)

IOS-XRv starts with a DSA (`ssh-dss`) host key which modern paramiko cannot verify.
Must replace it with RSA each time a new sandbox is reserved.

```bash
# In Ubuntu WSL2 — SSH to DevBox first
ssh developer@10.10.20.50

# From DevBox — SSH to IOS-XRv (DevBox supports legacy ssh-dss)
ssh -o HostKeyAlgorithms=+ssh-dss -o PubkeyAcceptedKeyTypes=+ssh-dss developer@10.10.20.35

# On IOS-XR — generate RSA host key
crypto key generate rsa
# Enter 2048 when prompted for modulus size

exit
exit
```

---

## Step 7 — Start ChatOps App (PowerShell)

```powershell
cd C:\deepak\Chatops\Chatopscode
.\venv\Scripts\Activate.ps1
uvicorn app:app --reload --host 0.0.0.0 --port 8001
```

Wait for: `Uvicorn running on http://0.0.0.0:8001`

---

## Step 8 — Get Auth Token (new PowerShell window)

```powershell
cd C:\deepak\Chatops\Chatopscode
.\get_token.ps1
```

**Expected:** `Token set: eyJhbGciOiJI...`

---

## Step 9 — Run Network Tests (PowerShell)

```powershell
.\network_tests.ps1        # interactive menu (XE / XR / NX-OS / Linux)
.\network_tests.ps1 xe     # Cat8kv only
.\network_tests.ps1 xr     # IOS-XRv only
.\network_tests.ps1 nx     # Nexus 9K only
.\network_tests.ps1 db     # DevBox (Linux) only
```

**Expected sections per device:**
| Section | Cat8kv (XE) | IOS-XRv (XR) | Nexus 9K (NX-OS) | DevBox (Linux) |
|---|---|---|---|---|
| Device Info | cat8000v · v17.12.02 | System · v6.5.3 | n9k · v9.3(5) | Ubuntu 22.04 |
| Interfaces | GigabitEthernet1 up | MgmtEth0/0/CPU0/0 up | mgmt0 up | eth0 up |
| Routes | default via 10.10.20.254 | default via 10.10.20.254 | default via 10.10.20.254 | default via 10.10.20.1 |
| BGP | no neighbors | no neighbors | no neighbors | N/A |
| OSPF | no neighbors | no neighbors | no neighbors | N/A |
| CPU & Memory | % + MB values | % + MB values | % + MB values | % + MB values |
| ARP | 10.10.20.x entries | 10.10.20.x entries | 10.10.20.x entries | 10.10.20.x entries |

---

## Step 10 — Open ChatOps UI

Navigate to `http://localhost:8001` in a browser and log in (admin / admin by default).

---

## ChatOps Network Features

### Network Dashboard
**Network → 📊 Network Dashboard**
- Device health cards: hostname, OS version, uptime, CPU bar, memory used/free
- Ping Matrix: click **📡 Run Ping Test** — shows device-to-device reachability (~30 sec)
- Network Alerts panel: BGP/interface alerts with Ack buttons

### Network Monitor
**Network → 🔭 Monitor Device…** — select device, then click:
- **🖧 Interfaces** — status table with IP, protocol, traffic rates
- **🗺 Routes** — routing table
- **⚙️ CPU/Memory** — utilization stats
- **🔗 BGP Neighbors** — neighbor state table
- **🔶 OSPF Neighbors** — neighbor state table
- **📋 ARP Table** — MAC mappings
- **📡 Ping Device** — ping a target from the device
- **🔀 Traceroute** — hop-by-hop path to a target
- **📜 Show Logs** — last N syslog entries
- **💾 View Backup** — show last stored config backup
- **📋 Config Diff** — diff running-config vs last backup (colored +/- output)

### OSPF / BGP Config Wizard
**Network → Configuration → ⚙️ OSPF / BGP Wizard…**

Generates and pushes correct per-OS config for all three Cisco routers:

| Protocol | IOS-XE | IOS-XR | NX-OS |
|---|---|---|---|
| OSPF | `router ospf N / network 10.10.20.0` | `router ospf N vrf Mgmt-intf` | `feature ospf / interface mgmt0` |
| BGP | `router bgp ASN / address-family ipv4` | `router bgp ASN / vrf Mgmt-intf` | `feature bgp / vrf management` |

**Expected results after Apply + Verify:**
- OSPF: cat8kv ↔ ios-xrv should reach **FULL** (same broadcast domain). NX-OS mgmt0 is in a restricted VRF — OSPF multicast adjacency does not form.
- BGP: all three should reach **Established** (BGP is TCP, works across management VRFs).

### Config Backup & Diff
1. **Network → 💾 Backup Config…** — saves running-config to database
2. Make a change on the device
3. **Network Monitor → 📋 Config Diff** — shows colored unified diff vs saved backup

---

## Sandbox Device Reference

> **IPs and credentials are fixed for every reservation of the "IOS XE on Cat8kv" blueprint.**
> Device registrations in ChatOps persist across reservations — no need to re-register.
> Only VPN username/password changes — check the Quick Access tab each time.

| Device      | IP           | Port | Username  | Password    | ChatOps Name | Type         |
|-------------|--------------|------|-----------|-------------|--------------|--------------|
| Cat8kv      | 10.10.20.48  | 22   | developer | C1sco12345  | cat8kv       | cisco_xe     |
| Cat8kv      | 10.10.20.48  | 830  | developer | C1sco12345  | —            | NETCONF      |
| IOS-XRv 9K  | 10.10.20.35  | 22   | developer | C1sco12345  | ios-xrv      | cisco_xr     |
| Nexus 9K    | 10.10.20.40  | 22   | admin     | RG!_Yw200   | nexus9k      | cisco_nxos   |
| DevBox      | 10.10.20.50  | 22   | developer | C1sco12345  | devbox       | linux        |

**What changes each reservation:**
- VPN username and password (check Quick Access tab)
- IOS-XRv SSH host key resets to DSA (redo Step 6 each time)

**What stays the same:**
- All device IPs (10.10.20.x) and SSH credentials
- VPN host: `devnetsandbox-usw1-reservation.cisco.com:20175`
- ChatOps device registrations

---

## Known Limitations

| Limitation | Detail |
|---|---|
| OSPF adjacency — all devices | OSPF uses multicast (224.0.0.5). IOS-XE OSPF runs in the global routing table; IOS-XR management is in `Mgmt-intf` VRF; NX-OS mgmt0 is in the management VRF. The virtual sandbox fabric does not deliver OSPF multicast across VRF boundaries, so no adjacency forms between any pair. **Use BGP instead** — it uses TCP unicast and works fine across all three. |
| IOS-XR ping direction | XR management is in `Mgmt-intf` VRF. ChatOps uses `ping vrf Mgmt-intf` automatically. |
| IOS-XR SSH sessions | XRv enforces a low concurrent session limit. Ping matrix serializes sessions per device. |
| Config diff — Linux | `show running-config` not applicable. Config Diff is Cisco-only. |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| VPN auth fails | Check Quick Access tab for correct username/password |
| `TcpTestSucceeded: False` | Re-run Step 3 (iptables) and Step 4 (route) |
| `Unable to connect` on ChatOps | App not running — repeat Step 7 |
| Token empty | Re-run `.\get_token.ps1` |
| Dashboard shows "Authentication failed" | Device credentials stale — use Network → DevNet Sandbox → Quick Connect, delete and re-register the device |
| IOS-XR `network_tests.ps1 xr` fails | Redo Step 6 (RSA key) — required after each new reservation |
| Sandbox expired | Reserve a new one at developer.cisco.com/sandbox |
