"""Generate Trident ChatOps marketing/sales PDF."""
from fpdf import FPDF
from datetime import date

FONT_DIR = ("/home/shukla_deepak77/.npm-global/lib/node_modules/openclaw"
            "/node_modules/pdfjs-dist/standard_fonts")

class PDF(FPDF):
    def setup_fonts(self):
        self.add_font("Lib", "",   f"{FONT_DIR}/LiberationSans-Regular.ttf")
        self.add_font("Lib", "B",  f"{FONT_DIR}/LiberationSans-Bold.ttf")
        self.add_font("Lib", "I",  f"{FONT_DIR}/LiberationSans-Italic.ttf")
        self.add_font("Lib", "BI", f"{FONT_DIR}/LiberationSans-BoldItalic.ttf")

    def header(self):
        if self.page_no() == 1:
            return
        self.set_fill_color(18, 18, 32)
        self.rect(0, 0, 210, 12, "F")
        self.set_font("Lib", "B", 8)
        self.set_text_color(167, 139, 250)
        self.set_y(3)
        self.cell(100, 6, "TRIDENT CHATOPS")
        self.set_text_color(100, 100, 130)
        self.cell(0, 6, "Confidential - Sales & Marketing", align="R")
        self.set_y(13)

    def footer(self):
        if self.page_no() == 1:
            return
        self.set_y(-12)
        self.set_fill_color(18, 18, 32)
        self.rect(0, self.get_y(), 210, 15, "F")
        self.set_font("Lib", "", 7.5)
        self.set_text_color(100, 100, 130)
        self.cell(0, 8, f"Page {self.page_no()}  |  www.tridentchatops.io  |  {date.today().strftime('%Y')}  Trident ChatOps. All rights reserved.", align="C")

    # ── helpers ────────────────────────────────────────────────────────────────
    def mc(self, w, h, txt, **kw):
        self.set_x(self.l_margin if w == 0 else self.get_x())
        self.multi_cell(w if w else self.epw, h, txt, **kw)

    def hline(self, r, g, b, y=None, lw=0.3):
        self.set_draw_color(r, g, b)
        self.set_line_width(lw)
        yy = y if y is not None else self.get_y()
        self.line(10, yy, 200, yy)

    def section_header(self, text, r=99, g=102, b=241):
        self.ln(3)
        self.hline(r, g, b, lw=0.5)
        self.ln(2)
        self.set_font("Lib", "B", 13)
        self.set_text_color(r, g, b)
        self.set_x(10)
        self.cell(0, 8, text)
        self.ln(8)
        self.set_text_color(30, 30, 30)

    def sub_header(self, text, r=30, g=120, b=200):
        self.ln(2)
        self.set_font("Lib", "B", 10.5)
        self.set_text_color(r, g, b)
        self.set_x(10)
        self.cell(0, 7, text)
        self.ln(6)
        self.set_text_color(40, 40, 55)

    def bullet(self, text, indent=14, color=(60, 60, 80)):
        self.set_font("Lib", "", 9)
        self.set_text_color(*color)
        self.set_x(indent)
        self.multi_cell(self.epw - (indent - 10), 5.5, f"  ->  {text}")
        self.set_text_color(40, 40, 55)

    def pain_box(self, title, items, x, y, w, h, bg=(255,240,240), tc=(180,30,30)):
        self.set_xy(x, y)
        self.set_fill_color(*bg)
        self.rect(x, y, w, h, "F")
        self.set_draw_color(200, 60, 60)
        self.set_line_width(0.4)
        self.rect(x, y, w, h)
        self.set_xy(x + 3, y + 3)
        self.set_font("Lib", "B", 9)
        self.set_text_color(*tc)
        self.cell(w - 6, 6, title)
        self.ln(7)
        self.set_font("Lib", "", 8)
        self.set_text_color(60, 30, 30)
        for item in items:
            self.set_x(x + 4)
            self.multi_cell(w - 8, 5, f"x  {item}")

    def solution_box(self, title, items, x, y, w, h, bg=(235,252,240), tc=(20,120,60)):
        self.set_xy(x, y)
        self.set_fill_color(*bg)
        self.rect(x, y, w, h, "F")
        self.set_draw_color(20, 160, 80)
        self.set_line_width(0.4)
        self.rect(x, y, w, h)
        self.set_xy(x + 3, y + 3)
        self.set_font("Lib", "B", 9)
        self.set_text_color(*tc)
        self.cell(w - 6, 6, title)
        self.ln(7)
        self.set_font("Lib", "", 8)
        self.set_text_color(20, 60, 30)
        for item in items:
            self.set_x(x + 4)
            self.multi_cell(w - 8, 5, f"v  {item}")

    def feature_card(self, icon, title, desc, x, y, w=58, h=34):
        self.set_xy(x, y)
        self.set_fill_color(28, 28, 50)
        self.rect(x, y, w, h, "F")
        self.set_draw_color(99, 102, 241)
        self.set_line_width(0.3)
        self.rect(x, y, w, h)
        self.set_xy(x + 3, y + 3)
        self.set_font("Lib", "B", 9)
        self.set_text_color(167, 139, 250)
        self.cell(w - 6, 6, f"{icon}  {title}")
        self.ln(6)
        self.set_xy(x + 3, self.get_y())
        self.set_font("Lib", "", 7.5)
        self.set_text_color(180, 185, 210)
        self.multi_cell(w - 6, 4.5, desc)
        self.set_text_color(40, 40, 55)

    def stat_box(self, value, label, x, y, w=42, h=24, vc=(255,200,50)):
        self.set_xy(x, y)
        self.set_fill_color(22, 22, 40)
        self.rect(x, y, w, h, "F")
        self.set_draw_color(*vc)
        self.set_line_width(0.5)
        self.rect(x, y, w, h)
        self.set_xy(x, y + 3)
        self.set_font("Lib", "B", 14)
        self.set_text_color(*vc)
        self.cell(w, 8, value, align="C")
        self.ln(8)
        self.set_xy(x, self.get_y())
        self.set_font("Lib", "", 7)
        self.set_text_color(160, 160, 190)
        self.cell(w, 5, label, align="C")
        self.set_text_color(40, 40, 55)


# ════════════════════════════════════════════════════════════════════════════════
pdf = PDF()
pdf.setup_fonts()
pdf.set_auto_page_break(auto=True, margin=14)
pdf.set_margins(10, 14, 10)

# ════════════════════════════════════════════════════════════════════════════════
# PAGE 1 — COVER
# ════════════════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.set_fill_color(12, 10, 28)
pdf.rect(0, 0, 210, 297, "F")

# gradient-feel top band
pdf.set_fill_color(30, 25, 70)
pdf.rect(0, 0, 210, 80, "F")

# accent line
pdf.set_draw_color(99, 102, 241)
pdf.set_line_width(1.5)
pdf.line(10, 82, 200, 82)

# logo area
pdf.set_y(18)
pdf.set_font("Lib", "B", 10)
pdf.set_text_color(99, 102, 241)
pdf.cell(0, 8, "TRIDENT  |  INTELLIGENT NETWORK OPERATIONS", align="C")
pdf.ln(12)

pdf.set_font("Lib", "B", 36)
pdf.set_text_color(226, 232, 240)
pdf.cell(0, 16, "Trident ChatOps", align="C")
pdf.ln(14)

pdf.set_font("Lib", "B", 17)
pdf.set_text_color(167, 139, 250)
pdf.cell(0, 9, "AI-Powered Network Operations Platform", align="C")
pdf.ln(9)

pdf.set_font("Lib", "I", 11)
pdf.set_text_color(148, 163, 184)
pdf.cell(0, 7, "Transforming L1/L2 Support  |  Reducing OpEx  |  Empowering Teams", align="C")
pdf.ln(22)

# 3 segment pills
segments = [("Enterprise", 99,102,241), ("Service Providers", 16,185,129), ("SMB / MSP", 245,158,11)]
start_x = 22
for label, r, g, b in segments:
    pdf.set_xy(start_x, pdf.get_y())
    pdf.set_fill_color(r, g, b)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Lib", "B", 9)
    pdf.rect(start_x, pdf.get_y(), 52, 10, "F")
    pdf.cell(52, 10, label, align="C")
    start_x += 58

pdf.ln(20)

# value props row
props = [
    ("60-80%", "Reduction in\nMTTR"),
    ("3x", "Faster Incident\nResolution"),
    ("40%", "OpEx\nSavings"),
    ("Day 1", "Productive for\nJunior Engineers"),
]
sx = 13
for val, lbl in props:
    pdf.stat_box(val, lbl.replace("\n", " "), sx, pdf.get_y(), w=43, h=26,
                 vc=(167,139,250))
    sx += 47

pdf.set_y(175)
pdf.set_draw_color(50, 50, 80)
pdf.set_line_width(0.3)
pdf.line(10, pdf.get_y(), 200, pdf.get_y())
pdf.ln(6)

pdf.set_font("Lib", "", 9)
pdf.set_text_color(100, 100, 140)
pdf.cell(0, 6,
    "Supports: Arista EOS  |  Cisco IOS / IOS-XE / IOS-XR / NX-OS  |  Juniper JunOS  |  VyOS  |  Linux",
    align="C")
pdf.ln(7)
pdf.set_font("Lib", "I", 8.5)
pdf.cell(0, 5, f"Prepared for Enterprise Sales  |  {date.today().strftime('%B %Y')}", align="C")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 2 — THE PROBLEM
# ════════════════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.section_header("The Industry Problem: Network Operations is Broken")

pdf.set_font("Lib", "", 9.5)
pdf.set_text_color(60, 60, 80)
pdf.set_x(10)
pdf.multi_cell(0, 5.5,
    "Every organisation operating a network faces a common set of painful, expensive, and recurring problems. "
    "Skilled engineers spend hours on repetitive L1/L2 tasks. Junior staff lack the tools and confidence to act. "
    "Downtime is prolonged because information is scattered across multiple CLI screens, ticketing systems, and runbooks.")
pdf.ln(5)

# 3-column pain layout
pdf.set_y(pdf.get_y())
y_start = pdf.get_y()

pdf.pain_box("Enterprise (Cisco / Juniper / Arista)", [
    "100s of devices across DC, WAN, campus",
    "Skilled NOC engineers burned out on\n  repetitive CLI tasks",
    "MTTR of 45-90 min for simple L1 faults",
    "Tool sprawl: NMS, ITSM, CLI — no single\n  pane of glass",
    "Audit & compliance gaps across config\n  changes",
    "Shadow IT: engineers bypass process\n  for speed",
], 10, y_start, 58, 72)

pdf.pain_box("Service Providers", [
    "Thousands of customer CPE devices to\n  manage",
    "SLA breaches due to slow fault isolation",
    "L1 agent ramp-up takes 3-6 months",
    "No self-service for customers — every\n  query hits NOC",
    "High OPEX from manual monitoring\n  and polling",
    "Scaling NOC headcount is expensive",
], 76, y_start, 58, 72)

pdf.pain_box("SMB / MSP (L1/L2 Support Focus)", [
    "Small teams can't justify expensive NMS\n  platforms",
    "Inexperienced staff make config errors\n  on live devices",
    "No runbook enforcement — tribal\n  knowledge only",
    "Can't afford 24/7 senior engineer\n  on standby",
    "Manual reporting to management\n  wastes hours",
    "Zero visibility until a customer\n  complains",
], 142, y_start, 58, 72)

pdf.set_y(y_start + 76)
pdf.ln(4)

pdf.set_fill_color(40, 15, 15)
pdf.set_draw_color(200, 60, 60)
pdf.set_line_width(0.4)
pdf.rect(10, pdf.get_y(), 190, 18, "F")
pdf.rect(10, pdf.get_y(), 190, 18)
pdf.set_xy(14, pdf.get_y() + 2)
pdf.set_font("Lib", "B", 9)
pdf.set_text_color(255, 120, 120)
pdf.cell(0, 6, "Industry Cost of Poor Network Operations:")
pdf.ln(6)
pdf.set_x(14)
pdf.set_font("Lib", "", 8.5)
pdf.set_text_color(220, 180, 180)
pdf.cell(0, 6,
    "Average network downtime costs $5,600/min (Gartner).  NOC L1/L2 engineer fully loaded cost: $80K-$120K/yr.  "
    "60% of incidents are repeat L1 issues solvable by automation.")
pdf.ln(22)

pdf.section_header("The Trident ChatOps Answer", r=16, g=185, b=129)

pdf.set_font("Lib", "", 9.5)
pdf.set_text_color(40, 60, 50)
pdf.set_x(10)
pdf.multi_cell(0, 5.5,
    "Trident ChatOps is a single, unified AI-assisted operations platform. Engineers interact through a natural-language "
    "chat interface to execute network commands, manage incidents, run automated playbooks, and generate reports — "
    "all without leaving the browser. Junior staff can perform L1/L2 tasks confidently on day one.")
pdf.ln(5)

y2 = pdf.get_y()
pdf.solution_box("Enterprise", [
    "Single pane: chat + alerts + network + tickets",
    "Role-based access — safe delegation to L1/L2",
    "Full audit trail of every command & change",
    "Push config with built-in diff & backup",
    "BGP/OSPF visibility in one click",
], 10, y2, 58, 56)

pdf.solution_box("Service Providers", [
    "Bulk device import via CSV/JSON",
    "Per-device monitoring, backup, push config",
    "Runbook automation for repeat fault types",
    "Real-time alerts with acknowledgement",
    "PDF SLA reports auto-generated",
], 76, y2, 58, 56)

pdf.solution_box("SMB / MSP", [
    "Affordable: runs on a single Linux VM",
    "Chat-guided L1/L2 — no CLI expertise needed",
    "Built-in KB: standard fixes at fingertips",
    "Ticket creation & tracking built in",
    "Junior engineer = senior engineer output",
], 142, y2, 58, 56)


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 3 — FEATURES
# ════════════════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.section_header("Platform Features")

features = [
    (">>", "AI Chat Interface",
     "Natural-language commands. Ask 'show bgp neighbors ceos1' or 'ping 10.0.0.1 on router1'. No CLI expertise required."),
    ("#", "Multi-Vendor Support",
     "Arista EOS, Cisco IOS/XE/XR/NX-OS, Juniper JunOS, VyOS, Linux. One platform, any vendor."),
    ("@", "Network Dashboard",
     "Live ping matrix across all devices, per-device health cards with CPU, memory, version, uptime."),
    ("!", "Real-Time Monitoring",
     "Interface status, BGP/OSPF neighbors, ARP/MAC tables, routes, interface errors, port-channels, VLANs, STP."),
    ("%", "Config Backup & Diff",
     "One-click config backup per device. Visual diff between live config and last backup catches unauthorised changes."),
    ("~", "Config Push",
     "Push CLI commands to any device from the browser. Backup is auto-taken before every push."),
    ("+", "Alert Management",
     "Predictive + threshold alerts with severity levels. Acknowledge all. Critical-only filter. Synced to chat."),
    ("*", "Incident & Ticketing",
     "Create, track, and close tickets without leaving ChatOps. AI-generated RCA drafts for faster post-mortems."),
    ("&", "Runbook Automation",
     "Built-in runbooks for disk, logs, services, cache. Custom runbook builder for organisation-specific playbooks."),
    ("?", "Knowledge Base",
     "Searchable internal KB. Attach fix articles to recurring alerts. Junior engineers self-serve before escalating."),
    ("$", "Bulk Device Import",
     "Import entire device inventory from CSV or JSON. Credentials verified via live SSH before saving."),
    ("^", "OSPF / BGP Wizard",
     "Point-and-click OSPF and BGP configuration across multiple devices simultaneously with preview before apply."),
    ("=", "Reports & Analytics",
     "7-day PDF reports, Prometheus metrics export, daily summary, audit log, analytics trends."),
    (">", "Role-Based Access",
     "Admin, operator, and viewer roles. Fine-grained control over who can read vs. who can push changes."),
    ("<", "Audit & Compliance",
     "Every command, config change, and login is logged with timestamp and user. Full traceability."),
    ("~", "DevNet / Lab Ready",
     "Quick-connect to Cisco DevNet sandboxes and Containerlab virtual labs for testing before production."),
]

cols = 3
card_w = 59
card_h = 32
gap = 5
sx_start = 10
sy = pdf.get_y()
col = 0
row_y = sy

for i, (icon, title, desc) in enumerate(features):
    cx = sx_start + col * (card_w + gap)
    if row_y + card_h > 270:
        pdf.add_page()
        row_y = pdf.get_y()
    pdf.feature_card(icon, title, desc, cx, row_y, w=card_w, h=card_h)
    col += 1
    if col >= cols:
        col = 0
        row_y += card_h + 4


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 4 — COST SAVINGS & ROI
# ════════════════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.section_header("Cost Savings & ROI")

# ROI table header
def row(cells, bold=False, bg=(240,240,255), tc=(30,30,60)):
    widths = [65, 55, 60]
    pdf.set_fill_color(*bg)
    pdf.set_text_color(*tc)
    pdf.set_font("Lib", "B" if bold else "", 8.5)
    pdf.set_x(10)
    for i, (w, cell) in enumerate(zip(widths, cells)):
        pdf.cell(w, 7, cell, border=1, fill=True)
    pdf.ln()

row(["Cost Area", "Without Trident ChatOps", "With Trident ChatOps"], bold=True,
    bg=(30,28,70), tc=(200,200,240))
data = [
    ("L1/L2 Engineer per shift",       "2-3 engineers @ $80K/yr ea.",    "1 engineer handles 3x workload"),
    ("Mean Time to Resolve (MTTR)",    "45-90 min per incident",          "10-20 min — chat-guided resolution"),
    ("Config change errors",           "5-10% human error rate",          "<1% with backup + diff + verification"),
    ("Onboarding new NOC staff",       "3-6 months to productivity",      "Day 1 productive with chat + KB"),
    ("Downtime cost (per incident)",   "$5,600/min x avg 60 min = $336K", "Reduced to ~$56K (90% less downtime)"),
    ("Compliance / audit prep",        "2-3 days manual log gathering",   "Instant audit log export"),
    ("Reporting",                      "4-8 hrs/week manual reports",     "Auto PDF + analytics, near zero effort"),
    ("Tool licensing (NMS + ITSM)",    "$50K-$200K/yr per platform",      "Single platform, fraction of the cost"),
]
alt = False
for cells in data:
    row(cells, bg=(248,248,255) if alt else (238,238,252))
    alt = not alt

pdf.ln(6)

# Savings estimator
pdf.set_fill_color(20, 18, 45)
pdf.set_draw_color(99, 102, 241)
pdf.set_line_width(0.5)
pdf.rect(10, pdf.get_y(), 190, 40, "F")
pdf.rect(10, pdf.get_y(), 190, 40)
pdf.set_xy(14, pdf.get_y() + 4)
pdf.set_font("Lib", "B", 10)
pdf.set_text_color(167, 139, 250)
pdf.cell(0, 7, "Sample Annual Savings — Mid-Size Enterprise (50 devices, 10-person NOC)")
pdf.ln(8)
savings = [
    ("Engineer cost reduction (2 FTE saved)", "$160,000"),
    ("Downtime reduction (10 incidents/yr, 60 min avg)", "$280,000"),
    ("Tool consolidation (replace NMS + ITSM)", "$120,000"),
    ("Productivity gains (reporting, runbooks)", "$40,000"),
]
sx = 14
for label, value in savings:
    pdf.set_x(sx)
    pdf.set_font("Lib", "", 8.5)
    pdf.set_text_color(180, 185, 210)
    pdf.cell(120, 5.5, label)
    pdf.set_font("Lib", "B", 8.5)
    pdf.set_text_color(110, 220, 140)
    pdf.cell(40, 5.5, value)
    pdf.ln(5.5)

pdf.set_x(14)
pdf.set_font("Lib", "B", 9.5)
pdf.set_text_color(255, 220, 80)
pdf.cell(120, 7, "Estimated Total Annual Saving")
pdf.set_font("Lib", "B", 11)
pdf.set_text_color(80, 255, 150)
pdf.cell(40, 7, "$600,000+")
pdf.ln(12)

pdf.section_header("Empowering Junior Engineers — The L1/L2 Multiplier")

pdf.set_font("Lib", "", 9.5)
pdf.set_text_color(50, 55, 70)
pdf.set_x(10)
pdf.multi_cell(0, 5.5,
    "One of the most significant hidden costs in network operations is the experience gap. "
    "Senior engineers are bottlenecked by L1/L2 tasks that could be handled by less experienced staff "
    "if given the right tools. Trident ChatOps closes that gap:")
pdf.ln(4)

junior_points = [
    ("Chat-guided commands", "No need to memorise CLI syntax. Type 'show bgp neighbors ceos1' and get a formatted, colour-coded result."),
    ("Built-in Knowledge Base", "Standard fixes and procedures embedded in the platform. Engineers self-serve before escalating."),
    ("Runbook enforcement", "Automated playbooks for the top 20 repeat incidents. Consistent, error-free execution every time."),
    ("Config safety net", "Automatic backup before every config push. Diff view shows exactly what will change. No more 'oops' moments."),
    ("Role-based guardrails", "Junior staff get read + limited-write access. Destructive commands reserved for senior roles."),
    ("Ticket & audit trail", "Every action logged. Junior engineers have a full record of what they did and when — safe to act."),
]
for title, desc in junior_points:
    pdf.set_x(12)
    pdf.set_font("Lib", "B", 9)
    pdf.set_text_color(99, 102, 241)
    pdf.cell(52, 5.5, title)
    pdf.set_font("Lib", "", 9)
    pdf.set_text_color(50, 55, 70)
    pdf.multi_cell(0, 5.5, desc)
    pdf.ln(1)


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 5 — FLEXIBILITY & CUSTOMISATION
# ════════════════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.section_header("Flexibility & Customisation")

pdf.set_font("Lib", "", 9.5)
pdf.set_text_color(50, 55, 70)
pdf.set_x(10)
pdf.multi_cell(0, 5.5,
    "Trident ChatOps is not a locked appliance. It is a modular, API-first platform built on open standards. "
    "Every layer is customisable — from the chat commands to the device drivers, runbooks, and integrations. "
    "Organisations can extend the platform on day one without waiting for a vendor release cycle.")
pdf.ln(5)

sections = [
    ("Add New Vendors / Device Types", [
        "Plug in any device supported by Netmiko or NETCONF/YANG (ncclient) — new vendor in hours, not weeks",
        "Community Netmiko supports 80+ device types out of the box",
        "Custom device drivers can be added for proprietary or niche hardware",
        "Per-vendor command templates for show, config, and health commands",
    ]),
    ("Custom Chat Commands", [
        "New natural-language commands added directly in the router layer — no recompile needed",
        "Regex-based pattern matching supports flexible phrasing ('show bgp', 'bgp neighbors for X', 'check bgp on X')",
        "Commands can call internal functions, external APIs, or shell scripts",
        "Multi-step workflows: a single chat command can chain multiple device queries",
    ]),
    ("Custom Runbooks", [
        "Built-in Runbook Builder UI — create, name, and save automation scripts from the browser",
        "Runbooks support any shell command, CLI snippet, or Python function",
        "Triggered manually via chat or menu, or scheduled as automated health checks",
        "Organisation-specific playbooks: ISP provisioning, CPE onboarding, maintenance windows",
    ]),
    ("Alerting & Thresholds", [
        "Alert thresholds configurable per metric: CPU, memory, disk, interface error rate",
        "Custom alert categories and severity levels",
        "Notification channels: Slack, email, webhook — all configurable in the settings panel",
        "Predictive alerting based on trend analysis of stored metrics",
    ]),
    ("Integration Ecosystem", [
        "REST API on every function — integrate with ServiceNow, Jira, PagerDuty, Splunk",
        "Prometheus metrics export endpoint for Grafana dashboards",
        "Webhook support for inbound alerts from existing monitoring systems",
        "LDAP / SSO integration ready for enterprise identity management",
    ]),
    ("Deployment Flexibility", [
        "Runs on a single Linux VM (2 vCPU, 4 GB RAM minimum) — no Kubernetes required",
        "Docker-ready for containerised deployments",
        "Air-gapped / private cloud deployment supported — no external dependencies",
        "Multi-tenant architecture available for MSPs managing multiple customers",
    ]),
]

for title, items in sections:
    if pdf.get_y() > 248:
        pdf.add_page()
    pdf.sub_header(title)
    for item in items:
        pdf.bullet(item)
    pdf.ln(2)


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 6 — COMPETITIVE POSITIONING
# ════════════════════════════════════════════════════════════════════════════════
pdf.add_page()
pdf.section_header("Why Trident ChatOps vs. the Alternatives")

def comp_row(feature, traditional, chatops, bold=False):
    pdf.set_x(10)
    bg_t = (28,28,50) if bold else (22,20,45)
    pdf.set_fill_color(*bg_t)
    pdf.set_draw_color(60, 60, 100)
    pdf.set_line_width(0.2)
    pdf.set_font("Lib", "B" if bold else "", 8.5)
    pdf.set_text_color(200, 200, 230) if bold else pdf.set_text_color(160, 165, 200)
    pdf.cell(65, 7, feature, border=1, fill=True)
    pdf.set_fill_color(50, 18, 18)
    pdf.set_text_color(220, 130, 130)
    pdf.set_font("Lib", "", 8)
    pdf.cell(62, 7, traditional, border=1, fill=True)
    pdf.set_fill_color(18, 50, 30)
    pdf.set_text_color(100, 220, 140)
    pdf.cell(63, 7, chatops, border=1, fill=True)
    pdf.ln()

comp_row("", "Traditional NMS / CLI Tools", "Trident ChatOps", bold=True)
comparisons = [
    ("Ease of use",              "Requires CLI expertise",          "Chat interface — works for all levels"),
    ("Vendor support",           "Often single-vendor",             "Multi-vendor, plug-in architecture"),
    ("L1/L2 enablement",         "Senior engineer dependency",      "Junior-ready on day 1"),
    ("Deployment",               "Complex, multi-server install",   "Single VM, 30-minute setup"),
    ("Cost",                     "$50K-$200K+/yr licensing",        "Fraction of cost, open platform"),
    ("Customisation",            "Vendor release cycle (months)",   "Custom commands/runbooks in hours"),
    ("Ticketing & ITSM",         "Separate tool required",          "Built-in ticket management"),
    ("Config management",        "Separate tool (Ansible/etc.)",    "Built-in: push, backup, diff"),
    ("Runbook automation",       "External scripting required",     "Built-in builder and executor"),
    ("Knowledge base",           "Wiki or SharePoint (separate)",   "Integrated, searchable KB"),
    ("Audit & compliance",       "Log scraping from NMS",           "Native audit log, instant export"),
    ("Alert management",         "NMS only, no correlation",        "Predictive alerts + acknowledgement"),
    ("AI assistance",            "None",                            "Natural language, context-aware chat"),
    ("API-first",                "Limited / proprietary APIs",      "Full REST API on all functions"),
    ("Multi-tenancy (MSP)",      "Expensive add-on",               "Built-in role & access control"),
]
alt = False
for cells in comparisons:
    pdf.set_fill_color(22,20,45) if not alt else pdf.set_fill_color(26,24,50)
    comp_row(*cells)
    alt = not alt

pdf.ln(6)
pdf.set_fill_color(20, 18, 45)
pdf.set_draw_color(99, 102, 241)
pdf.set_line_width(0.4)
pdf.rect(10, pdf.get_y(), 190, 14, "F")
pdf.rect(10, pdf.get_y(), 190, 14)
pdf.set_xy(14, pdf.get_y() + 3)
pdf.set_font("Lib", "B", 9)
pdf.set_text_color(167, 139, 250)
pdf.cell(0, 7,
    "Trident ChatOps delivers what it takes 3-4 separate tools to achieve — at a fraction of the cost and complexity.")


# ════════════════════════════════════════════════════════════════════════════════
# PAGE 7 — CALL TO ACTION / NEXT STEPS
# ════════════════════════════════════════════════════════════════════════════════
pdf.add_page()

pdf.set_fill_color(12, 10, 28)
pdf.rect(0, 0, 210, 297, "F")
pdf.set_fill_color(25, 22, 60)
pdf.rect(0, 0, 210, 60, "F")

pdf.set_y(16)
pdf.set_font("Lib", "B", 22)
pdf.set_text_color(226, 232, 240)
pdf.cell(0, 12, "Ready to Transform Your Network Operations?", align="C")
pdf.ln(10)
pdf.set_font("Lib", "", 11)
pdf.set_text_color(148, 163, 184)
pdf.cell(0, 7, "See Trident ChatOps in action with your own devices — live demo in under 30 minutes.", align="C")

pdf.set_y(68)
pdf.section_header("Get Started in 3 Steps", r=16, g=185, b=129)

steps = [
    ("1", "Request a Live Demo",
     "We connect Trident ChatOps to your lab or DevNet sandbox and demonstrate real L1/L2 workflows "
     "with your device types. No commitment required."),
    ("2", "Pilot Deployment",
     "Deploy on a single VM in your environment. Import your device list via CSV. "
     "Up and running in under 1 hour. Pilot period: 30 days, fully supported."),
    ("3", "Production Rollout",
     "Scale to full device inventory. Integrate with your ITSM and monitoring stack. "
     "Custom runbooks and commands developed together with your team."),
]

for num, title, desc in steps:
    if pdf.get_y() > 240:
        break
    y_s = pdf.get_y()
    pdf.set_fill_color(30, 28, 70)
    pdf.set_draw_color(16, 185, 129)
    pdf.set_line_width(0.5)
    pdf.rect(10, y_s, 190, 30, "F")
    pdf.rect(10, y_s, 190, 30)
    pdf.set_xy(14, y_s + 4)
    pdf.set_font("Lib", "B", 20)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(14, 10, num)
    pdf.set_font("Lib", "B", 11)
    pdf.set_text_color(226, 232, 240)
    pdf.cell(0, 10, title)
    pdf.ln(9)
    pdf.set_x(28)
    pdf.set_font("Lib", "", 9)
    pdf.set_text_color(160, 170, 200)
    pdf.multi_cell(172, 5.5, desc)
    pdf.ln(6)

pdf.ln(4)
pdf.section_header("Contact & Licensing", r=245, g=158, b=11)

pdf.set_font("Lib", "", 9.5)
pdf.set_text_color(160, 165, 200)
pdf.set_x(10)
pdf.multi_cell(0, 6,
    "Trident ChatOps is available under flexible licensing models to suit every organisation size:")
pdf.ln(3)

pricing = [
    ("SMB / MSP Starter",    "Up to 25 devices",  "Ideal for small teams and MSPs"),
    ("Service Provider",     "Up to 500 devices", "Multi-tenant, SLA reporting, bulk import"),
    ("Enterprise",           "Unlimited devices", "Full API, custom integrations, dedicated support"),
    ("Custom / On-Premise",  "Any scale",         "Air-gapped, white-label, and OEM options available"),
]
pdf.set_x(10)
for tier, scope, desc in pricing:
    pdf.set_x(12)
    pdf.set_font("Lib", "B", 9)
    pdf.set_text_color(245, 158, 11)
    pdf.cell(50, 6, tier)
    pdf.set_font("Lib", "", 9)
    pdf.set_text_color(130, 200, 255)
    pdf.cell(40, 6, scope)
    pdf.set_text_color(160, 165, 200)
    pdf.cell(0, 6, desc)
    pdf.ln(6)

pdf.ln(4)
pdf.set_fill_color(22, 20, 50)
pdf.set_draw_color(99, 102, 241)
pdf.set_line_width(0.5)
pdf.rect(10, pdf.get_y(), 190, 22, "F")
pdf.rect(10, pdf.get_y(), 190, 22)
pdf.set_xy(14, pdf.get_y() + 4)
pdf.set_font("Lib", "B", 10)
pdf.set_text_color(167, 139, 250)
pdf.cell(0, 7, "Contact Us")
pdf.ln(7)
pdf.set_x(14)
pdf.set_font("Lib", "", 9)
pdf.set_text_color(180, 185, 220)
pdf.cell(60, 5.5, "Email:  sales@tridentchatops.io")
pdf.cell(60, 5.5, "Web:  www.tridentchatops.io")
pdf.cell(0,  5.5, "Demo:  calendly.com/tridentchatops")

# ── Output ────────────────────────────────────────────────────────────────────
out = "/home/shukla_deepak77/chatops/ChatOps/trident_chatops_marketing.pdf"
pdf.output(out)
print(f"PDF written to: {out}")
