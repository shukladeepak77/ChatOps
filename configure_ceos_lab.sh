#!/bin/bash
# Configure IP addresses on ceos1, ceos2, ceos3 Ethernet interfaces

PASS="admin123"

configure_device() {
    local host=$1
    local name=$2
    local commands=$3

    echo "Configuring $name ($host)..."
    sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no admin@$host << EOF
enable
configure
$commands
end
write memory
EOF
    echo "$name done."
    echo ""
}

# ceos1: Et1=10.0.12.1/24, Et2=10.0.13.1/24
configure_device "172.20.20.3" "ceos1" "
interface Ethernet1
 no switchport
 ip address 10.0.12.1/24
interface Ethernet2
 no switchport
 ip address 10.0.13.1/24
"

# ceos2: Et1=10.0.12.2/24, Et2=10.0.23.1/24
configure_device "172.20.20.4" "ceos2" "
interface Ethernet1
 no switchport
 ip address 10.0.12.2/24
interface Ethernet2
 no switchport
 ip address 10.0.23.1/24
"

# ceos3: Et1=10.0.23.2/24, Et2=10.0.13.2/24
configure_device "172.20.20.2" "ceos3" "
interface Ethernet1
 no switchport
 ip address 10.0.23.2/24
interface Ethernet2
 no switchport
 ip address 10.0.13.2/24
"

echo "All devices configured."
