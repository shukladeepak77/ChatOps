"""Generate detailed manual test plan PDF for Trident ChatOps Console."""
from fpdf import FPDF
from datetime import date

FONT_DIR = ("/home/shukla_deepak77/.npm-global/lib/node_modules/openclaw"
            "/node_modules/pdfjs-dist/standard_fonts")

REGULAR  = f"{FONT_DIR}/LiberationSans-Regular.ttf"
BOLD     = f"{FONT_DIR}/LiberationSans-Bold.ttf"
ITALIC   = f"{FONT_DIR}/LiberationSans-Italic.ttf"
BOLDITAL = f"{FONT_DIR}/LiberationSans-BoldItalic.ttf"


class PDF(FPDF):
    def setup_fonts(self):
        self.add_font("Lib", "",   REGULAR)
        self.add_font("Lib", "B",  BOLD)
        self.add_font("Lib", "I",  ITALIC)
        self.add_font("Lib", "BI", BOLDITAL)

    def header(self):
        self.set_font("Lib", "B", 9)
        self.set_text_color(100, 100, 120)
        self.cell(0, 8, "Trident ChatOps Console - Manual Test Plan", align="R")
        self.ln(2)
        self.set_draw_color(99, 102, 241)
        self.set_line_width(0.4)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)

    def footer(self):
        self.set_y(-13)
        self.set_font("Lib", "", 8)
        self.set_text_color(130, 130, 150)
        self.cell(0, 8, f"Page {self.page_no()} | Confidential - Internal Use Only", align="C")

    def cover(self):
        self.add_page()
        self.set_fill_color(20, 20, 35)
        self.rect(0, 0, 210, 297, "F")
        self.set_y(60)
        self.set_font("Lib", "B", 28)
        self.set_text_color(167, 139, 250)
        self.cell(0, 14, "Trident ChatOps Console", align="C")
        self.ln(12)
        self.set_font("Lib", "B", 18)
        self.set_text_color(226, 232, 240)
        self.cell(0, 10, "Manual Test Plan", align="C")
        self.ln(8)
        self.set_font("Lib", "", 12)
        self.set_text_color(148, 163, 184)
        self.cell(0, 8, "Chatbot Commands & Menu Interface", align="C")
        self.ln(20)
        self.set_draw_color(99, 102, 241)
        self.set_line_width(0.6)
        self.line(50, self.get_y(), 160, self.get_y())
        self.ln(16)
        self.set_font("Lib", "", 11)
        self.set_text_color(148, 163, 184)
        self.cell(0, 7, f"Version: 1.0", align="C"); self.ln(6)
        self.cell(0, 7, f"Date: {date.today().strftime('%B %d, %Y')}", align="C"); self.ln(6)
        self.cell(0, 7, "Environment: Arista cEOS Lab (ceos1, ceos2, ceos3)", align="C")

    def section_title(self, text, level=1):
        self.ln(4)
        if level == 1:
            self.set_font("Lib", "B", 13)
            self.set_text_color(99, 102, 241)
            self.set_draw_color(99, 102, 241)
            self.set_line_width(0.3)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(2)
            self.cell(0, 8, text)
            self.ln(2)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(4)
        else:
            self.set_font("Lib", "B", 11)
            self.set_text_color(30, 100, 180)
            self.cell(0, 7, text)
            self.ln(3)
        self.set_text_color(30, 30, 30)

    def labeled_row(self, label, text, fill_color, text_color, bold_text=False):
        self.set_fill_color(*fill_color)
        self.set_text_color(*text_color)
        self.set_font("Lib", "B", 8)
        self.multi_cell(0, 6, f"[{label}]  {text}" if not bold_text else f"[{label}]", fill=True)
        self.set_text_color(30, 30, 30)

    def mc(self, text, fill=True):
        """multi_cell helper that resets x to left margin first."""
        self.set_x(self.l_margin)
        self.multi_cell(self.epw, 6, text, fill=fill)

    def test_case(self, tc_id, title, steps, expected, notes=""):
        if self.get_y() > 250:
            self.add_page()
        # Header row
        self.set_fill_color(45, 45, 65)
        self.set_text_color(200, 200, 220)
        self.set_font("Lib", "B", 9)
        self.mc(f"{tc_id}  |  {title}")
        # Steps
        self.set_fill_color(248, 248, 252)
        self.set_text_color(40, 40, 60)
        self.set_font("Lib", "B", 8)
        for i, step in enumerate(steps, 1):
            prefix = "Steps:" if i == 1 else "      "
            self.mc(f"{prefix}  {i}. {step}")
        # Expected
        self.set_fill_color(235, 250, 242)
        self.set_text_color(20, 100, 60)
        self.set_font("Lib", "B", 8)
        self.mc(f"Expected:  {expected}")
        # Notes
        if notes:
            self.set_fill_color(254, 252, 232)
            self.set_text_color(100, 70, 10)
            self.set_font("Lib", "B", 8)
            self.mc(f"Note:  {notes}")
        # Result row
        self.set_fill_color(240, 240, 250)
        self.set_text_color(80, 80, 100)
        self.set_font("Lib", "", 8)
        self.mc("Result:  [ ] Pass  [ ] Fail      Tester: _______________________   Date: ____________")
        self.ln(3)
        self.set_text_color(30, 30, 30)

    def info_box(self, text, color=(230, 240, 255)):
        self.set_fill_color(*color)
        self.set_text_color(30, 50, 100)
        self.set_font("Lib", "I", 8)
        self.multi_cell(0, 6, text, fill=True, border=0)
        self.set_text_color(30, 30, 30)
        self.ln(2)


pdf = PDF()
pdf.setup_fonts()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.set_margins(10, 14, 10)

# Cover
pdf.cover()

# TOC
pdf.add_page()
pdf.set_font("Lib", "B", 14)
pdf.set_text_color(80, 60, 160)
pdf.cell(0, 10, "Table of Contents")
pdf.ln(10)
pdf.ln(2)
toc = [
    ("1",  "Test Environment & Prerequisites"),
    ("2",  "Authentication"),
    ("3",  "Chatbot - System & Host Commands"),
    ("4",  "Chatbot - Alert Commands"),
    ("5",  "Chatbot - Network Device Commands"),
    ("6",  "Chatbot - Ticket Commands"),
    ("7",  "Chatbot - Runbook Commands"),
    ("8",  "Chatbot - Reporting & Analytics"),
    ("9",  "Menu - System Menu"),
    ("10", "Menu - Alerts Menu"),
    ("11", "Menu - Network: Device Management"),
    ("12", "Menu - Network: Monitor Device"),
    ("13", "Menu - Network: Config & Backup"),
    ("14", "Menu - Tickets & Incidents"),
    ("15", "Menu - Runbooks"),
    ("16", "Menu - Reports & Analytics"),
    ("17", "Menu - Settings & Admin"),
    ("18", "Cross-Cutting & Edge Cases"),
]
pdf.set_font("Lib", "", 10)
pdf.set_text_color(40, 40, 60)
for num, title in toc:
    pdf.cell(12, 7, num)
    pdf.cell(0, 7, title)
    pdf.ln()

# =============================================================================
# SECTION 1 - ENVIRONMENT
# =============================================================================
pdf.add_page()
pdf.section_title("1. Test Environment & Prerequisites")
pdf.set_font("Lib", "", 9)
pdf.set_text_color(40, 40, 60)
prereqs = [
    ("GCP VM",            "e2-standard-4, Debian 13, Docker 29.5, Containerlab v0.75"),
    ("cEOS Lab",          "3 nodes: ceos1 (172.20.20.3), ceos2 (172.20.20.4), ceos3 (172.20.20.5)"),
    ("Routing",           "OSPF Area 0 converged (all FULL), eBGP Established (AS 65001/65002/65003)"),
    ("ChatOps Server",    "uvicorn app:app --host 0.0.0.0 --port 8001"),
    ("Browser",           "Chrome / Firefox - access via http://<GCP-IP>:8001/chatops"),
    ("Credentials",       "admin / admin123  (admin role)"),
    ("Devices Registered","ceos1, ceos2, ceos3 registered as arista_eos in Network Devices"),
]
for k, v in prereqs:
    pdf.set_font("Lib", "B", 9); pdf.cell(42, 6, k + ":")
    pdf.set_font("Lib", "",  9); pdf.cell(0,  6, v); pdf.ln()
pdf.ln(3)
pdf.info_box("Start server before testing:  source venv/bin/activate && uvicorn app:app --host 0.0.0.0 --port 8001")

# =============================================================================
# SECTION 2 - AUTHENTICATION
# =============================================================================
pdf.section_title("2. Authentication")

pdf.test_case("TC-AUTH-01", "Login with valid credentials",
    ["Open http://<GCP-IP>:8001/chatops in browser",
     "Enter username: admin, password: admin123",
     "Click Sign In"],
    "Dashboard loads. Header shows 'Trident ChatOps Console'. Chat input is active. Sign Out button visible.")

pdf.test_case("TC-AUTH-02", "Login with invalid credentials",
    ["Enter username: admin, password: wrongpass",
     "Click Sign In"],
    "Error message displayed. Dashboard does NOT load.")

pdf.test_case("TC-AUTH-03", "Sign Out",
    ["While logged in, click Sign Out in top-right corner"],
    "Login screen shown. All panels cleared.")

pdf.test_case("TC-AUTH-04", "Session persistence on page refresh",
    ["Log in successfully", "Press F5 to refresh the page"],
    "User remains logged in. No re-login required within the session.")

# =============================================================================
# SECTION 3 - CHATBOT: SYSTEM & HOST
# =============================================================================
pdf.add_page()
pdf.section_title("3. Chatbot - System & Host Commands")
pdf.info_box("Type each command in the chat input and press Enter. Verify the bot response appears in the chat window.")

pdf.test_case("TC-CHAT-SYS-01", "system health",
    ["Type: system health", "Press Enter"],
    "Response shows CPU %, memory used/free, disk usage, load average, uptime. All values are numeric.")

pdf.test_case("TC-CHAT-SYS-02", "check disk",
    ["Type: check disk", "Press Enter"],
    "Disk usage table: filesystem, size, used, available, % used, mount point.")

pdf.test_case("TC-CHAT-SYS-03", "check memory",
    ["Type: check memory", "Press Enter"],
    "Memory stats: total, used, free, cached.")

pdf.test_case("TC-CHAT-SYS-04", "check cpu",
    ["Type: check cpu", "Press Enter"],
    "CPU usage % shown per core or aggregate.")

pdf.test_case("TC-CHAT-SYS-05", "check uptime",
    ["Type: check uptime", "Press Enter"],
    "System uptime and load averages displayed.")

pdf.test_case("TC-CHAT-SYS-06", "top processes",
    ["Type: top processes", "Press Enter"],
    "Top 10 processes by CPU/memory with PID, name, CPU%, MEM%.")

pdf.test_case("TC-CHAT-SYS-07", "check ports",
    ["Type: check ports", "Press Enter"],
    "Listening ports listed with protocol, port number, and process name.")

pdf.test_case("TC-CHAT-SYS-08", "check failed services",
    ["Type: check failed services", "Press Enter"],
    "Failed systemd services listed, or confirmation that no services have failed.")

pdf.test_case("TC-CHAT-SYS-09", "check ip",
    ["Type: check ip", "Press Enter"],
    "Network interface IPs listed.")

pdf.test_case("TC-CHAT-SYS-10", "check routes",
    ["Type: check routes", "Press Enter"],
    "Host routing table displayed.")

pdf.test_case("TC-CHAT-SYS-11", "check network",
    ["Type: check network", "Press Enter"],
    "Network stats: bytes sent/received, packets, errors.")

pdf.test_case("TC-CHAT-SYS-12", "check connections",
    ["Type: check connections", "Press Enter"],
    "Active network connections listed.")

# =============================================================================
# SECTION 4 - CHATBOT: ALERTS
# =============================================================================
pdf.add_page()
pdf.section_title("4. Chatbot - Alert Commands")

pdf.test_case("TC-CHAT-ALERT-01", "show alerts",
    ["Type: show alerts", "Press Enter"],
    "Current alerts listed with severity, timestamp, and message. If none, shows 'No active alerts'.")

pdf.test_case("TC-CHAT-ALERT-02", "show critical alerts",
    ["Type: show critical alerts", "Press Enter"],
    "Only CRITICAL severity alerts shown.")

pdf.test_case("TC-CHAT-ALERT-03", "show unacked alerts",
    ["Type: show unacked alerts", "Press Enter"],
    "Only unacknowledged alerts shown.")

pdf.test_case("TC-CHAT-ALERT-04", "show predictive alerts",
    ["Type: show predictive alerts", "Press Enter"],
    "Predictive / trend-based alerts shown based on metric history.")

# =============================================================================
# SECTION 5 - CHATBOT: NETWORK DEVICES
# =============================================================================
pdf.add_page()
pdf.section_title("5. Chatbot - Network Device Commands")
pdf.info_box("Pre-condition: ceos1, ceos2, ceos3 registered as arista_eos. Lab OSPF and BGP must be converged.")

pdf.test_case("TC-CHAT-NET-01", "show interfaces <device>",
    ["Type: show interfaces ceos1", "Press Enter"],
    "Interface table: Ethernet1, Ethernet2, Management0 with IPs and link status.",
    "Expected IPs: Eth1=10.0.12.1/24, Eth2=10.0.13.1/24, Mgmt0=172.20.20.3/24")

pdf.test_case("TC-CHAT-NET-02", "show interfaces for ceos2 and ceos3",
    ["Type: show interfaces ceos2",
     "Type: show interfaces ceos3"],
    "Each device shows correct interfaces with IPs per lab topology.")

pdf.test_case("TC-CHAT-NET-03", "show ospf neighbors <device>",
    ["Type: show ospf neighbors ceos1", "Press Enter"],
    "OSPF neighbor table: 2.2.2.2 and 3.3.3.3 both FULL, with interface and address.")

pdf.test_case("TC-CHAT-NET-04", "ospf neighbor for <device>  (natural language)",
    ["Type: ospf neighbor for ceos1", "Press Enter"],
    "Same result as TC-CHAT-NET-03. Natural-language variant accepted.")

pdf.test_case("TC-CHAT-NET-05", "show bgp neighbors <device>",
    ["Type: show bgp neighbors ceos1", "Press Enter"],
    "BGP summary: 2 peers (172.20.20.4, 172.20.20.5) both Established, with AS and prefix counts.")

pdf.test_case("TC-CHAT-NET-06", "bgp neighbor for <device>  (natural language)",
    ["Type: bgp neighbor for ceos1", "Press Enter"],
    "Same result as TC-CHAT-NET-05.")

pdf.test_case("TC-CHAT-NET-07", "ping <IP> on <device>",
    ["Type: ping 172.20.20.4 on ceos1", "Press Enter"],
    "Response: 'Ping from ceos1 to 172.20.20.4: 100% success rate'")

pdf.test_case("TC-CHAT-NET-08", "Full mesh ping verification",
    ["ping 172.20.20.5 on ceos1",
     "ping 172.20.20.3 on ceos2",
     "ping 172.20.20.5 on ceos2",
     "ping 172.20.20.3 on ceos3",
     "ping 172.20.20.4 on ceos3"],
    "All 5 pings return 100% success rate.")

pdf.test_case("TC-CHAT-NET-09", "Invalid device name",
    ["Type: show interfaces nonexistent", "Press Enter"],
    "Friendly error: 'Network device nonexistent not found'. No server crash.")

# =============================================================================
# SECTION 6 - CHATBOT: TICKETS
# =============================================================================
pdf.add_page()
pdf.section_title("6. Chatbot - Ticket Commands")

pdf.test_case("TC-CHAT-TKT-01", "show tickets",
    ["Type: show tickets", "Press Enter"],
    "Open tickets listed with ID, title, priority, and status.")

pdf.test_case("TC-CHAT-TKT-02", "list tickets",
    ["Type: list tickets", "Press Enter"],
    "All tickets (open and closed) listed.")

# =============================================================================
# SECTION 7 - CHATBOT: RUNBOOKS
# =============================================================================
pdf.section_title("7. Chatbot - Runbook Commands")

pdf.test_case("TC-CHAT-RB-01", "list runbooks",
    ["Type: list runbooks", "Press Enter"],
    "Built-in runbooks listed: disk_breakdown, large_logs, listening_services, clear_tmp, flush_cache, rotate_logs.")

pdf.test_case("TC-CHAT-RB-02", "list custom runbooks",
    ["Type: list custom runbooks", "Press Enter"],
    "User-created runbooks listed, or 'No custom runbooks' message.")

pdf.test_case("TC-CHAT-RB-03", "run runbook disk_breakdown",
    ["Type: run runbook disk_breakdown", "Press Enter"],
    "Runbook executes and returns disk breakdown output.")

# =============================================================================
# SECTION 8 - CHATBOT: REPORTING
# =============================================================================
pdf.section_title("8. Chatbot - Reporting & Analytics")

pdf.test_case("TC-CHAT-RPT-01", "show analytics",
    ["Type: show analytics", "Press Enter"],
    "Analytics summary: alert counts, top metrics, trends.")

pdf.test_case("TC-CHAT-RPT-02", "show report",
    ["Type: show report", "Press Enter"],
    "Daily report: key system metrics and alert summary.")

pdf.test_case("TC-CHAT-RPT-03", "download pdf report",
    ["Type: download pdf report", "Press Enter"],
    "PDF report generated. Browser download dialog appears.")

pdf.test_case("TC-CHAT-RPT-04", "show system config",
    ["Type: show system config", "Press Enter"],
    "System configuration displayed (thresholds, notification settings, etc.).")

pdf.test_case("TC-CHAT-RPT-05", "show audit log",
    ["Type: show audit log", "Press Enter"],
    "Audit trail shown: logins, commands run, devices accessed.")

# =============================================================================
# SECTION 9 - MENU: SYSTEM
# =============================================================================
pdf.add_page()
pdf.section_title("9. Menu - System Menu")
pdf.info_box("Click 'System' in the top navigation bar to expand the dropdown, then click each item.")

pdf.section_title("9.1 Health & Resources", level=2)
pdf.test_case("TC-MENU-SYS-01", "System Health",
    ["Click System > System Health"],
    "Chat shows system health summary: CPU, memory, disk, load, uptime.")

pdf.test_case("TC-MENU-SYS-02", "Check Disk / Memory / CPU / Uptime",
    ["Click System > Check Disk",
     "Repeat for Check Memory, Check CPU, Check Uptime"],
    "Each produces the same output as the equivalent chat command.")

pdf.test_case("TC-MENU-SYS-03", "Top Processes",
    ["Click System > Top Processes"],
    "Process table shown in chat.")

pdf.test_case("TC-MENU-SYS-04", "Check Ports and Failed Services",
    ["Click System > Check Ports",
     "Click System > Failed Services"],
    "Listening ports and failed service list shown respectively.")

pdf.section_title("9.2 Network (Host Level)", level=2)
pdf.test_case("TC-MENU-SYS-05", "Check IP / Routes / Network Stats / Connections",
    ["Click each: Check IP, Check Routes, Network Stats, Connections"],
    "Each item produces equivalent output in chat.")

pdf.test_case("TC-MENU-SYS-06", "DNS Lookup modal",
    ["Click System > DNS Lookup...",
     "Enter: google.com",
     "Click Lookup"],
    "Modal opens. Resolved IPs shown. Result synced to chat.",
    "Requires outbound DNS from GCP VM.")

pdf.section_title("9.3 Services", level=2)
pdf.test_case("TC-MENU-SYS-07", "Service Status modal",
    ["Click System > Service Status...",
     "Enter service name: ssh",
     "Click Check Status"],
    "Modal shows active/inactive status, PID, uptime.")

pdf.test_case("TC-MENU-SYS-08", "Restart Service modal",
    ["Click System > Restart Service...",
     "Enter a non-critical test service name",
     "Click Restart"],
    "Restart result shown in modal.",
    "WARNING: Do NOT restart ssh or critical services during testing.")

# =============================================================================
# SECTION 10 - MENU: ALERTS
# =============================================================================
pdf.add_page()
pdf.section_title("10. Menu - Alerts Menu")

pdf.test_case("TC-MENU-ALERT-01", "Show All / Critical / Unacked / Predictive Alerts",
    ["Click Alerts > Show All Alerts",
     "Repeat for Critical Only, Unacknowledged, Predictive Alerts"],
    "Each option filters alerts correctly in chat output.")

pdf.test_case("TC-MENU-ALERT-02", "Acknowledge All",
    ["Click Alerts > Acknowledge All",
     "Confirm in the confirmation modal"],
    "All active alerts marked acknowledged. Alert count badge resets to zero.")

pdf.test_case("TC-MENU-ALERT-03", "Open Alerts Panel",
    ["Click Alerts > Open Alerts Panel"],
    "UI switches to the Alerts tab. Alert list rendered in the panel.")

# =============================================================================
# SECTION 11 - MENU: NETWORK - DEVICE MANAGEMENT
# =============================================================================
pdf.add_page()
pdf.section_title("11. Menu - Network: Device Management")

pdf.test_case("TC-MENU-NET-01", "List Devices",
    ["Click Network > List Devices"],
    "Network Devices modal shows ceos1, ceos2, ceos3 with type, host IP, and action buttons (Check, Ifaces, Delete).")

pdf.test_case("TC-MENU-NET-02", "Add Device",
    ["Click Network > Add Device...",
     "Name: test-device, Host: 1.2.3.4, Type: Arista EOS, Port: 22, User: admin, Password: admin",
     "Click Add Device"],
    "Device added and appears in list.",
    "Delete this test device immediately after.")

pdf.test_case("TC-MENU-NET-03", "Delete Device",
    ["In Network Devices list, click the delete (trash) icon next to test-device"],
    "Device removed from list. Confirmation of deletion shown.")

pdf.test_case("TC-MENU-NET-04", "Check Device button",
    ["Click Network > List Devices",
     "Click 'Check' button next to ceos1"],
    "Result shows: ceos1 hostname, model (cEOSLab), version (4.33.8M), uptime. Synced to chat.")

pdf.test_case("TC-MENU-NET-05", "Interface Status from device list",
    ["Click 'Ifaces' button next to ceos1 in device list"],
    "Interface Status modal opens pre-selected to ceos1. Shows Ethernet1, Ethernet2, Management0.")

pdf.test_case("TC-MENU-NET-06", "Network Dashboard",
    ["Click Network > Network Dashboard"],
    "Dashboard card per device: hostname, version, memory, uptime. Ping matrix shows 100% for all pairs.")

pdf.test_case("TC-MENU-NET-07", "Interface Status (from menu)",
    ["Click Network > Interface Status...",
     "Select ceos2 from dropdown"],
    "Interface table for ceos2 shown: Ethernet1 (10.0.12.2), Ethernet2 (10.0.23.2), Management0.")

# =============================================================================
# SECTION 12 - MENU: NETWORK - MONITOR DEVICE
# =============================================================================
pdf.add_page()
pdf.section_title("12. Menu - Network: Monitor Device")
pdf.info_box("Click Network > Monitor Device... to open the Network Monitor modal. Select a device then click buttons below.")

pdf.test_case("TC-MENU-MON-01", "Interfaces",
    ["Open Monitor Device, select ceos1", "Click Interfaces button"],
    "Interface table: Ethernet1, Ethernet2, Management0 with IPs and status.")

pdf.test_case("TC-MENU-MON-02", "Routes",
    ["Select ceos1, click Routes"],
    "Routing table with OSPF learned and connected routes.")

pdf.test_case("TC-MENU-MON-03", "CPU / Memory",
    ["Select ceos1, click CPU/Memory"],
    "CPU % and memory (total / used / free) displayed for ceos1.")

pdf.test_case("TC-MENU-MON-04", "BGP Neighbors",
    ["Select ceos1, click BGP Neighbors"],
    "BGP table: 2 peers (AS 65002 and AS 65003), both Established, with prefix counts and uptime.")

pdf.test_case("TC-MENU-MON-05", "OSPF Neighbors",
    ["Select ceos1, click OSPF Neighbors"],
    "OSPF table: 2.2.2.2 and 3.3.3.3 both FULL, with interface name and neighbor address.")

pdf.test_case("TC-MENU-MON-06", "ARP Table",
    ["Select ceos1, click ARP Table"],
    "ARP entries: IP address, MAC address, interface.")

pdf.test_case("TC-MENU-MON-07", "CDP / LLDP Neighbors",
    ["Select ceos1, click CDP/LLDP Neighbors"],
    "Neighbor discovery table, or 'No CDP/LLDP neighbors' if not enabled.")

pdf.test_case("TC-MENU-MON-08", "Interface Errors",
    ["Select ceos1, click Interface Errors"],
    "Error counters per interface: input errors, CRC, drops.")

pdf.test_case("TC-MENU-MON-09", "MAC Table",
    ["Select ceos1, click MAC Table"],
    "MAC address table with VLAN, MAC, port.")

pdf.test_case("TC-MENU-MON-10", "VLAN Audit",
    ["Select ceos1, click VLAN Audit"],
    "VLAN list, or 'No VLANs configured' for a pure L3 device.")

pdf.test_case("TC-MENU-MON-11", "Spanning Tree",
    ["Select ceos1, click Spanning Tree"],
    "STP status per VLAN, or 'Not applicable' for L3-only device.")

pdf.test_case("TC-MENU-MON-12", "Port Channel",
    ["Select ceos1, click Port Channel"],
    "Port-channel summary, or 'No port-channels configured'.")

pdf.test_case("TC-MENU-MON-13", "Ping via Monitor Device",
    ["Select ceos1, enter target: 172.20.20.4, click Run (Ping)"],
    "Ping result: 100% success rate.")

pdf.test_case("TC-MENU-MON-14", "Traceroute via Monitor Device",
    ["Select ceos1, enter target: 172.20.20.5, click Run (Traceroute)"],
    "Traceroute hops displayed from ceos1 to 172.20.20.5.")

pdf.test_case("TC-MENU-MON-15", "Device Logs",
    ["Select ceos1, click Fetch (Device Logs)"],
    "Last 50 lines of syslog displayed.")

pdf.test_case("TC-MENU-MON-16", "Test across all three devices",
    ["Repeat TC-MENU-MON-04 and TC-MENU-MON-05 for ceos2 and ceos3"],
    "Each device returns correct BGP and OSPF neighbors confirming full-mesh adjacency.")

# =============================================================================
# SECTION 13 - MENU: NETWORK - CONFIG & BACKUP
# =============================================================================
pdf.add_page()
pdf.section_title("13. Menu - Network: Config & Backup")

pdf.test_case("TC-MENU-CFG-01", "Backup Config",
    ["Click Network > Backup Config...",
     "Select ceos1",
     "Click Backup Now"],
    "Running config pulled and stored. Success message with line count shown.")

pdf.test_case("TC-MENU-CFG-02", "View Latest Backup",
    ["After TC-MENU-CFG-01, click Network > Monitor Device",
     "Select ceos1, click View Backup"],
    "Stored backup config displayed in results pane.")

pdf.test_case("TC-MENU-CFG-03", "Config Diff",
    ["After backup, add a description on ceos1: 'interface Ethernet1 / description test-diff'",
     "In Monitor Device, select ceos1, click Config Diff"],
    "Diff shows added description line compared to stored backup.")

pdf.test_case("TC-MENU-CFG-04", "Push Config",
    ["Click Network > Push Config...",
     "Select ceos1",
     "Commands: interface Ethernet1 / description Test-Push",
     "Click Push Config"],
    "Config applied. Success message shown. Verify on device with 'show interfaces Ethernet1'.",
    "Revert after test: push 'no description' on Ethernet1.")

pdf.test_case("TC-MENU-CFG-05", "OSPF / BGP Config Wizard",
    ["Click Network > OSPF / BGP Wizard...",
     "Review OSPF tab - process ID, area, devices listed",
     "Switch to BGP tab - verify AS number and devices"],
    "Wizard opens with correct device list. Config preview shown. Do NOT click Apply unless intentional.")

pdf.test_case("TC-MENU-CFG-06", "DevNet Quick Connect",
    ["Click Network > Quick Connect..."],
    "DevNet Sandbox modal opens with connection fields.")

# =============================================================================
# SECTION 14 - TICKETS
# =============================================================================
pdf.add_page()
pdf.section_title("14. Menu - Tickets & Incidents")

pdf.test_case("TC-MENU-TKT-01", "Create Ticket",
    ["Click Tickets > Create Ticket",
     "Title: Test Ticket, Priority: Medium, Description: Manual testing",
     "Click Create Ticket"],
    "Ticket created with ID. Appears in ticket list.")

pdf.test_case("TC-MENU-TKT-02", "Show open tickets",
    ["Click Tickets > Show Tickets"],
    "Open tickets listed with ID, title, priority, status, date.")

pdf.test_case("TC-MENU-TKT-03", "Show all tickets",
    ["Click Tickets > All Tickets"],
    "All tickets including closed ones listed.")

pdf.test_case("TC-MENU-TKT-04", "New Ticket from ticket list",
    ["In Show Tickets modal, click New Ticket button"],
    "Show Tickets modal closes. Create Ticket modal opens.")

pdf.test_case("TC-MENU-TKT-05", "RCA Draft",
    ["Click Tickets > RCA Draft...",
     "Describe an incident",
     "Click Generate RCA"],
    "AI-generated RCA draft displayed.")

# =============================================================================
# SECTION 15 - RUNBOOKS
# =============================================================================
pdf.section_title("15. Menu - Runbooks")

pdf.test_case("TC-MENU-RB-01", "List Runbooks",
    ["Click Runbooks > List Runbooks"],
    "All built-in runbook names shown in chat.")

pdf.test_case("TC-MENU-RB-02", "Run Disk Breakdown",
    ["Click Runbooks > Disk Breakdown",
     "Click Execute in modal"],
    "Disk breakdown output shown: directories sorted by size.")

pdf.test_case("TC-MENU-RB-03", "Run Large Logs",
    ["Click Runbooks > Large Logs, Execute"],
    "Large log files listed with sizes.")

pdf.test_case("TC-MENU-RB-04", "Run Listening Services",
    ["Click Runbooks > Listening Services, Execute"],
    "Active listening ports and services listed.")

pdf.test_case("TC-MENU-RB-05", "Runbook Builder - create and run custom runbook",
    ["Click Runbooks > Runbook Builder...",
     "Create runbook named 'test-rb' with command: echo hello",
     "Save, then run it"],
    "Custom runbook saved, appears in 'list custom runbooks', executes successfully.")

# =============================================================================
# SECTION 16 - REPORTS
# =============================================================================
pdf.add_page()
pdf.section_title("16. Menu - Reports & Analytics")

pdf.test_case("TC-MENU-RPT-01", "Show Analytics",
    ["Click Reports > Show Analytics"],
    "Analytics summary in chat: alert trends, top metrics.")

pdf.test_case("TC-MENU-RPT-02", "Prometheus Metrics",
    ["Click Reports > Prometheus Metrics"],
    "Prometheus-format metrics text displayed.")

pdf.test_case("TC-MENU-RPT-03", "Download PDF Report (7 days)",
    ["Click Reports > Download PDF (7d)"],
    "7-day PDF report generated. Browser download dialog appears.")

pdf.test_case("TC-MENU-RPT-04", "Daily Report",
    ["Click Reports > Daily Report"],
    "Daily report summary shown in chat.")

pdf.test_case("TC-MENU-RPT-05", "Open Metrics Panel",
    ["Click Reports > Open Metrics Panel"],
    "UI switches to Metrics tab. Charts and graphs visible.")

# =============================================================================
# SECTION 17 - SETTINGS & ADMIN
# =============================================================================
pdf.section_title("17. Menu - Settings & Admin")

pdf.test_case("TC-MENU-ADM-01", "List Users",
    ["Click Settings > List Users"],
    "User Management modal shows all users with username and role.")

pdf.test_case("TC-MENU-ADM-02", "Add User",
    ["Click Settings > Add User...",
     "Username: testuser, Password: Test123!, Role: operator",
     "Click Create User"],
    "User created. Appears in user list.",
    "Delete testuser after this test.")

pdf.test_case("TC-MENU-ADM-03", "List Nodes",
    ["Click Settings > List Nodes"],
    "Nodes modal shows registered monitoring nodes.")

pdf.test_case("TC-MENU-ADM-04", "Open Config Panel",
    ["Click Settings > Open Config Panel"],
    "UI switches to Config tab with editable system settings.")

pdf.test_case("TC-MENU-ADM-05", "Open KB Panel",
    ["Click Settings > Open KB Panel"],
    "UI switches to Knowledge Base tab. Articles listed or empty state.")

pdf.test_case("TC-MENU-ADM-06", "Audit Log",
    ["Click Settings > Audit Log (or type: show audit log)"],
    "Audit trail shown: logins, commands, device access with timestamps.")

pdf.test_case("TC-MENU-ADM-07", "Test Slack",
    ["Click Settings > Test Slack"],
    "Slack test message sent. Success/failure shown in chat.",
    "Requires Slack webhook configured in chatops_config.json.")

pdf.test_case("TC-MENU-ADM-08", "Run Tests",
    ["Click Settings > Run Tests"],
    "Internal test suite runs. Pass/fail summary shown.")

# =============================================================================
# SECTION 18 - EDGE CASES
# =============================================================================
pdf.add_page()
pdf.section_title("18. Cross-Cutting & Edge Cases")

pdf.test_case("TC-EDGE-01", "Unrecognized chat command",
    ["Type: hello world", "Press Enter"],
    "Bot replies with helpful suggestions. No crash. Suggests 'help' command.")

pdf.test_case("TC-EDGE-02", "help command",
    ["Type: help", "Press Enter"],
    "Full list of available commands shown in chat.")

pdf.test_case("TC-EDGE-03", "Device command when ceos1 is offline",
    ["Run: docker stop ceos1",
     "Type: show interfaces ceos1",
     "Run: docker start ceos1  (restore after test)"],
    "Graceful error: SSH timeout or connection refused. No server crash or 500 error.",
    "Always restart ceos1 after this test to restore the lab.")

pdf.test_case("TC-EDGE-04", "Concurrent commands",
    ["Send: system health",
     "Immediately send: show interfaces ceos1"],
    "Both commands complete and return correct independent results.")

pdf.test_case("TC-EDGE-05", "Close modal with Escape key",
    ["Open any modal (e.g. Interface Status)",
     "Press Escape key"],
    "Modal closes cleanly. No errors in console.")

pdf.test_case("TC-EDGE-06", "Close modal by clicking backdrop",
    ["Open any modal",
     "Click on the dark area outside the modal"],
    "Modal closes cleanly.")

pdf.test_case("TC-EDGE-07", "Browser tab title",
    ["Open the app in browser"],
    "Browser tab shows 'Trident ChatOps Console'.")

pdf.test_case("TC-EDGE-08", "Refresh button on Monitor Device",
    ["Open Monitor Device for ceos1, load BGP Neighbors",
     "Click Refresh button"],
    "Data reloads fresh from the device.")

pdf.test_case("TC-EDGE-09", "Ping matrix in Network Dashboard",
    ["Click Network > Network Dashboard",
     "Scroll to ping matrix section"],
    "All 6 device-pair combinations (ceos1-ceos2, ceos1-ceos3, ceos2-ceos3 in both directions) show 100%.")

pdf.test_case("TC-EDGE-10", "Empty inputs in Add Device modal",
    ["Open Network > Add Device...",
     "Leave all fields blank",
     "Click Add Device"],
    "Validation error shown. Device NOT added. No server crash.")

pdf.test_case("TC-EDGE-11", "Add duplicate device name",
    ["Try to add a device with name 'ceos1' (already exists)"],
    "Error shown: device already exists. Original record unchanged.")

pdf.test_case("TC-EDGE-12", "BGP and OSPF on ceos2 and ceos3",
    ["show bgp neighbors ceos2",
     "show ospf neighbors ceos2",
     "show bgp neighbors ceos3",
     "show ospf neighbors ceos3"],
    "Each device returns correct peers confirming full-mesh adjacency from all sides.")

# Output
out = "/home/shukla_deepak77/chatops/ChatOps/chatops_manual_test_plan.pdf"
pdf.output(out)
print(f"PDF written to: {out}")
