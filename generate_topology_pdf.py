#!/usr/bin/env python3
from fpdf import FPDF
from datetime import datetime

class TopologyPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_fill_color(30, 41, 59)
        self.set_text_color(255, 255, 255)
        self.rect(0, 0, 210, 20, "F")
        self.cell(0, 20, "ChatOps Lab - Network Topology", align="C", new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  Page {self.page_no()}", align="C")


pdf = TopologyPDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)

# ── Overview ──────────────────────────────────────────────────────────────────
pdf.ln(5)
pdf.set_font("Helvetica", "B", 13)
pdf.set_text_color(30, 64, 175)
pdf.cell(0, 8, "Lab Overview", new_x="LMARGIN", new_y="NEXT")
pdf.set_draw_color(30, 64, 175)
pdf.line(10, pdf.get_y(), 200, pdf.get_y())
pdf.ln(3)

pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(0, 0, 0)
overview = [
    ("Platform",      "GCP VM - Debian 13 (trixie), e2-standard-4, 16 GB RAM, 30 GB SSD"),
    ("Containerlab",  "v0.75.0"),
    ("Docker",        "v29.5.0"),
    ("cEOS Image",    "Arista cEOS-lab 4.33.8M (64-bit)"),
    ("Lab Name",      "chatops-lab"),
    ("Nodes",         "3 x Arista cEOS routers (ceos1, ceos2, ceos3)"),
    ("Topology",      "Full mesh (triangle) - each node connected to both others"),
]
for label, value in overview:
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(45, 7, label + ":", new_x="RIGHT", new_y="TOP")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")

# ── Node Details ──────────────────────────────────────────────────────────────
pdf.ln(5)
pdf.set_font("Helvetica", "B", 13)
pdf.set_text_color(30, 64, 175)
pdf.cell(0, 8, "Node Details", new_x="LMARGIN", new_y="NEXT")
pdf.set_draw_color(30, 64, 175)
pdf.line(10, pdf.get_y(), 200, pdf.get_y())
pdf.ln(3)

nodes = [
    ("ceos1", "172.20.20.3", "10.0.12.1/24", "10.0.13.1/24"),
    ("ceos2", "172.20.20.4", "10.0.12.2/24", "10.0.23.1/24"),
    ("ceos3", "172.20.20.2", "10.0.23.2/24", "10.0.13.2/24"),
]

# Table header
pdf.set_fill_color(30, 41, 59)
pdf.set_text_color(255, 255, 255)
pdf.set_font("Helvetica", "B", 10)
pdf.cell(30, 8, "Node",       fill=True, border=1)
pdf.cell(40, 8, "Mgmt IP",    fill=True, border=1)
pdf.cell(50, 8, "Ethernet1",  fill=True, border=1)
pdf.cell(50, 8, "Ethernet2",  fill=True, border=1, new_x="LMARGIN", new_y="NEXT")

# Table rows
pdf.set_text_color(0, 0, 0)
pdf.set_font("Helvetica", "", 10)
colors = [(248, 250, 252), (255, 255, 255)]
for i, (name, mgmt, et1, et2) in enumerate(nodes):
    pdf.set_fill_color(*colors[i % 2])
    pdf.cell(30, 7, name, fill=True, border=1)
    pdf.cell(40, 7, mgmt, fill=True, border=1)
    pdf.cell(50, 7, et1,  fill=True, border=1)
    pdf.cell(50, 7, et2,  fill=True, border=1, new_x="LMARGIN", new_y="NEXT")

# ── Links ─────────────────────────────────────────────────────────────────────
pdf.ln(5)
pdf.set_font("Helvetica", "B", 13)
pdf.set_text_color(30, 64, 175)
pdf.cell(0, 8, "Links (Virtual Ethernet Cables)", new_x="LMARGIN", new_y="NEXT")
pdf.set_draw_color(30, 64, 175)
pdf.line(10, pdf.get_y(), 200, pdf.get_y())
pdf.ln(3)

pdf.set_fill_color(30, 41, 59)
pdf.set_text_color(255, 255, 255)
pdf.set_font("Helvetica", "B", 10)
pdf.cell(20, 8, "Link",       fill=True, border=1)
pdf.cell(50, 8, "Side A",     fill=True, border=1)
pdf.cell(50, 8, "Side B",     fill=True, border=1)
pdf.cell(60, 8, "Subnet",     fill=True, border=1, new_x="LMARGIN", new_y="NEXT")

links = [
    ("L1", "ceos1 - Ethernet1 (10.0.12.1)", "ceos2 - Ethernet1 (10.0.12.2)", "10.0.12.0/24"),
    ("L2", "ceos2 - Ethernet2 (10.0.23.1)", "ceos3 - Ethernet1 (10.0.23.2)", "10.0.23.0/24"),
    ("L3", "ceos1 - Ethernet2 (10.0.13.1)", "ceos3 - Ethernet2 (10.0.13.2)", "10.0.13.0/24"),
]

pdf.set_text_color(0, 0, 0)
pdf.set_font("Helvetica", "", 10)
for i, (link, a, b, subnet) in enumerate(links):
    pdf.set_fill_color(*colors[i % 2])
    pdf.cell(20, 7, link,   fill=True, border=1)
    pdf.cell(50, 7, a,      fill=True, border=1)
    pdf.cell(50, 7, b,      fill=True, border=1)
    pdf.cell(60, 7, subnet, fill=True, border=1, new_x="LMARGIN", new_y="NEXT")

# ── ASCII Topology Diagram ────────────────────────────────────────────────────
pdf.ln(5)
pdf.set_font("Helvetica", "B", 13)
pdf.set_text_color(30, 64, 175)
pdf.cell(0, 8, "Topology Diagram", new_x="LMARGIN", new_y="NEXT")
pdf.set_draw_color(30, 64, 175)
pdf.line(10, pdf.get_y(), 200, pdf.get_y())
pdf.ln(3)

pdf.set_font("Courier", "", 9)
pdf.set_text_color(30, 41, 59)
diagram = """
                  +---------------------------+
                  |  ceos1 (172.20.20.3)      |
                  |  Et1: 10.0.12.1/24        |
                  |  Et2: 10.0.13.1/24        |
                  +----------+----------------+
                             |           |
             10.0.12.0/24    |           |   10.0.13.0/24
                             |           |
          +------------------+       +---+----------------+
          |  ceos2 (172.20.20.4)     |  ceos3 (172.20.20.2) |
          |  Et1: 10.0.12.2/24       |  Et1: 10.0.23.2/24   |
          |  Et2: 10.0.23.1/24       |  Et2: 10.0.13.2/24   |
          +------------+-------------+---------+------------+
                       |                       |
                       +---  10.0.23.0/24  ----+
"""
for line in diagram.splitlines():
    pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")

# ── Credentials ───────────────────────────────────────────────────────────────
pdf.ln(5)
pdf.set_font("Helvetica", "B", 13)
pdf.set_text_color(30, 64, 175)
pdf.cell(0, 8, "Access Credentials (Lab Only)", new_x="LMARGIN", new_y="NEXT")
pdf.set_draw_color(30, 64, 175)
pdf.line(10, pdf.get_y(), 200, pdf.get_y())
pdf.ln(3)

pdf.set_font("Helvetica", "", 10)
pdf.set_text_color(0, 0, 0)
creds = [
    ("Username", "admin"),
    ("Password", "admin123"),
    ("SSH Port", "22"),
    ("ChatOps URL", "http://<GCP-IP>:8000/chatops"),
]
for label, value in creds:
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(40, 7, label + ":", new_x="RIGHT", new_y="TOP")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")

pdf.output("chatops_lab_topology.pdf")
print("PDF generated: chatops_lab_topology.pdf")
