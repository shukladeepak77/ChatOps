#!/usr/bin/env python3
from netmiko import ConnectHandler

devices = [
    {
        "name": "ceos1",
        "host": "172.20.20.3",
        "commands": [
            "interface Ethernet1", "no switchport", "ip address 10.0.12.1/24",
            "interface Ethernet2", "no switchport", "ip address 10.0.13.1/24",
        ],
    },
    {
        "name": "ceos2",
        "host": "172.20.20.4",
        "commands": [
            "interface Ethernet1", "no switchport", "ip address 10.0.12.2/24",
            "interface Ethernet2", "no switchport", "ip address 10.0.23.1/24",
        ],
    },
    {
        "name": "ceos3",
        "host": "172.20.20.2",
        "commands": [
            "interface Ethernet1", "no switchport", "ip address 10.0.23.2/24",
            "interface Ethernet2", "no switchport", "ip address 10.0.13.2/24",
        ],
    },
]

for dev in devices:
    print(f"Configuring {dev['name']} ({dev['host']})...")
    try:
        conn = ConnectHandler(
            device_type="arista_eos",
            host=dev["host"],
            username="admin",
            password="admin123",
            timeout=30,
            session_timeout=60,
            fast_cli=False,
        )
        output = conn.send_config_set(dev["commands"])
        conn.save_config()
        conn.disconnect()
        print(f"  Done.\n{output}\n")
    except Exception as e:
        print(f"  ERROR: {e}\n")

print("All devices configured.")
