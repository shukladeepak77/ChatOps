#!/usr/bin/env python3
"""
Generate a network topology PDF by pulling live data from the ChatOps API.

Usage:
    python3 generate_topology_pdf.py [--url URL] [--user USER] [--password PASSWORD]

Defaults:
    --url      http://localhost:8000
    --user     admin
    --password admin123
"""
import argparse
import ipaddress
import json
import urllib.request
import urllib.error
from datetime import datetime
from fpdf import FPDF


# ── CLI args ──────────────────────────────────────────────────────────────────

parser = argparse.ArgumentParser()
parser.add_argument("--url",      default="http://localhost:8000")
parser.add_argument("--user",     default="admin")
parser.add_argument("--password", default="admin123")
parser.add_argument("--output",   default="chatops_lab_topology.pdf")
args = parser.parse_args()

BASE = args.url.rstrip("/")


# ── API helpers ───────────────────────────────────────────────────────────────

def _request(path: str, token: str = None) -> dict:
    req = urllib.request.Request(f"{BASE}{path}")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())


def login(user: str, password: str) -> str:
    data = json.dumps({"username": user, "password": password}).encode()
    req = urllib.request.Request(
        f"{BASE}/chatops/auth/login", data=data,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read())["token"]


def get_devices(token: str) -> list:
    data = _request("/chatops/network/devices", token)
    return data if isinstance(data, list) else data.get("devices", [])


def get_interfaces(token: str, name: str) -> list:
    try:
        data = _request(f"/chatops/network/devices/{name}/interfaces", token)
        return data.get("interfaces", [])
    except Exception:
        return []


# ── Subnet inference: find links between devices ──────────────────────────────

def _network(ip_cidr: str) -> str:
    """Return network address string for an IP/prefix, e.g. '10.0.12.0/24'."""
    try:
        return str(ipaddress.ip_interface(ip_cidr).network)
    except Exception:
        return ""


def infer_links(device_ifaces: dict) -> list:
    """
    Given {device_name: [iface_dict, ...]}, return list of
    (link_id, dev_a, iface_a, ip_a, dev_b, iface_b, ip_b, subnet) tuples
    by matching interfaces that share the same subnet.
    """
    # subnet -> list of (device, interface, ip)
    subnet_map: dict = {}
    for dev, ifaces in device_ifaces.items():
        for iface in ifaces:
            ip = iface.get("ip", "")
            if not ip or ip == "unassigned":
                continue
            net = _network(ip)
            if not net:
                continue
            subnet_map.setdefault(net, []).append((dev, iface["interface"], ip))

    links = []
    link_id = 1
    for subnet, endpoints in subnet_map.items():
        if len(endpoints) == 2:
            a, b = endpoints
            links.append((
                f"L{link_id}",
                a[0], a[1], a[2],
                b[0], b[1], b[2],
                subnet,
            ))
            link_id += 1
    return links


# ── PDF class ─────────────────────────────────────────────────────────────────

class TopologyPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 16)
        self.set_fill_color(30, 41, 59)
        self.set_text_color(255, 255, 255)
        self.rect(0, 0, 210, 20, "F")
        self.cell(0, 20, "ChatOps - Network Topology Report", align="C",
                  new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(100, 100, 100)
        self.cell(
            0, 10,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  "
            f"Source: {BASE}  |  Page {self.page_no()}",
            align="C",
        )

    def section(self, title: str):
        self.ln(5)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(30, 64, 175)
        self.cell(0, 8, title, new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(30, 64, 175)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def kv(self, label: str, value: str):
        self.set_font("Helvetica", "B", 10)
        self.cell(45, 7, label + ":", new_x="RIGHT", new_y="TOP")
        self.set_font("Helvetica", "", 10)
        self.cell(0, 7, value, new_x="LMARGIN", new_y="NEXT")

    def table_header(self, cols: list):
        self.set_fill_color(30, 41, 59)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 10)
        for label, width in cols[:-1]:
            self.cell(width, 8, label, fill=True, border=1)
        label, width = cols[-1]
        self.cell(width, 8, label, fill=True, border=1, new_x="LMARGIN", new_y="NEXT")
        self.set_text_color(0, 0, 0)
        self.set_font("Helvetica", "", 10)

    def table_row(self, values: list, cols: list, row_idx: int):
        bg = (248, 250, 252) if row_idx % 2 == 0 else (255, 255, 255)
        self.set_fill_color(*bg)
        for (val, (_, width)) in zip(values[:-1], cols[:-1]):
            self.cell(width, 7, str(val), fill=True, border=1)
        val, (_, width) = values[-1], cols[-1]
        self.cell(width, 7, str(val), fill=True, border=1, new_x="LMARGIN", new_y="NEXT")


# ── Main ──────────────────────────────────────────────────────────────────────

print(f"Connecting to ChatOps at {BASE} ...")
token = login(args.user, args.password)
print("Logged in. Fetching devices ...")
devices = get_devices(token)
print(f"Found {len(devices)} device(s). Fetching interfaces ...")

device_ifaces = {}
for dev in devices:
    name = dev["name"]
    ifaces = get_interfaces(token, name)
    device_ifaces[name] = ifaces
    print(f"  {name}: {len(ifaces)} interface(s)")

links = infer_links(device_ifaces)
print(f"Inferred {len(links)} link(s) from shared subnets.")

# ── Build PDF ─────────────────────────────────────────────────────────────────

pdf = TopologyPDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)

# Overview
pdf.section("Overview")
pdf.kv("ChatOps URL", BASE)
pdf.kv("Generated",   datetime.now().strftime("%Y-%m-%d %H:%M"))
pdf.kv("Devices",     str(len(devices)))
pdf.kv("Links",       str(len(links)))

# Device summary table
pdf.section("Registered Devices")
dev_cols = [("Name", 35), ("Host", 45), ("Type", 35), ("Description", 75)]
pdf.table_header(dev_cols)
for i, dev in enumerate(devices):
    row = [
        dev.get("name", ""),
        dev.get("host", ""),
        dev.get("device_type", ""),
        (dev.get("description") or "")[:40],
    ]
    pdf.table_row(row, dev_cols, i)

# Per-device interface tables
pdf.section("Interfaces per Device")
iface_cols = [("Interface", 45), ("IP Address", 50), ("Status", 30), ("Protocol", 30), ("Errors", 35)]
for dev in devices:
    name = dev["name"]
    ifaces = device_ifaces.get(name, [])
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 7, f"{name}  ({dev['host']})", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    if not ifaces:
        pdf.set_font("Helvetica", "I", 9)
        pdf.cell(0, 6, "  No interfaces found (device may be unreachable)",
                 new_x="LMARGIN", new_y="NEXT")
        continue
    pdf.table_header(iface_cols)
    for i, iface in enumerate(ifaces):
        row = [
            iface.get("interface", ""),
            iface.get("ip", "unassigned"),
            iface.get("status", ""),
            iface.get("protocol", ""),
            str(iface.get("errors_in") or 0),
        ]
        pdf.table_row(row, iface_cols, i)
    pdf.ln(2)

# Links table
if links:
    pdf.section("Inferred Links (shared subnets)")
    link_cols = [("Link", 15), ("Device A", 35), ("Interface A", 35),
                 ("Device B", 35), ("Interface B", 35), ("Subnet", 35)]
    pdf.table_header(link_cols)
    for i, (lid, da, ia, ipa, db, ib, ipb, subnet) in enumerate(links):
        pdf.table_row([lid, da, f"{ia} ({ipa})", db, f"{ib} ({ipb})", subnet],
                      link_cols, i)

# ASCII topology diagram (devices + connections)
pdf.section("Topology Diagram")
pdf.set_font("Courier", "", 8)
pdf.set_text_color(30, 41, 59)

# Build simple text diagram
dev_names = [d["name"] for d in devices]
box_w = max((len(n) for n in dev_names), default=6) + 4

def box(name: str, host: str, ifaces: list) -> list:
    w = max(box_w, len(name) + 4, len(host) + 4)
    border = "+" + "-" * (w + 2) + "+"
    lines = [border, f"| {name.center(w)} |", f"| {host.center(w)} |"]
    for iface in ifaces:
        ip = iface.get("ip", "")
        if ip and ip != "unassigned":
            tag = f"{iface['interface']}: {ip}"
            lines.append(f"| {tag:<{w}} |")
    lines.append(border)
    return lines

for dev in devices:
    name = dev["name"]
    lines = box(name, dev["host"], device_ifaces.get(name, []))
    for line in lines:
        pdf.cell(0, 4, line, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

if links:
    pdf.ln(2)
    pdf.set_font("Courier", "B", 8)
    pdf.cell(0, 5, "Links:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Courier", "", 8)
    for lid, da, ia, ipa, db, ib, ipb, subnet in links:
        line = f"  {lid}: {da}/{ia} ({ipa}) <--[{subnet}]--> {db}/{ib} ({ipb})"
        pdf.cell(0, 4, line, new_x="LMARGIN", new_y="NEXT")

pdf.output(args.output)
print(f"\nPDF generated: {args.output}")
