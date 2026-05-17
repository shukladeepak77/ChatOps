#!/usr/bin/env python3
from netmiko import ConnectHandler

devices = [
    {
        "name": "ceos1",
        "host": "172.20.20.3",
        "router_id": "1.1.1.1",
        "interfaces": ["Ethernet1", "Ethernet2"],
    },
    {
        "name": "ceos2",
        "host": "172.20.20.4",
        "router_id": "2.2.2.2",
        "interfaces": ["Ethernet1", "Ethernet2"],
    },
    {
        "name": "ceos3",
        "host": "172.20.20.2",
        "router_id": "3.3.3.3",
        "interfaces": ["Ethernet1", "Ethernet2"],
    },
]

for dev in devices:
    print(f"Configuring OSPF on {dev['name']} ({dev['host']})...")
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
        commands = [
            "router ospf 1",
            f"router-id {dev['router_id']}",
            "exit",
        ]
        for iface in dev["interfaces"]:
            commands += [
                f"interface {iface}",
                "ip ospf area 0.0.0.0",
                "exit",
            ]
        output = conn.send_config_set(commands)
        conn.save_config()
        conn.disconnect()
        print(f"  Done.\n")
    except Exception as e:
        print(f"  ERROR: {e}\n")

print("OSPF configuration complete.")
