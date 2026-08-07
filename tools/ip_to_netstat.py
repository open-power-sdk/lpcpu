#!/usr/bin/env python3
"""
ip_to_netstat.py
Converts 'ip -s link' output to 'netstat -in' format
"""

import sys
import re

def parse_ip_link_output(lines):
    """Parse ip -s link output and extract interface statistics."""
    interfaces = []
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for interface line (starts with number and colon)
        if re.match(r'^\d+:', line):
            # Extract interface name
            parts = line.split()
            iface = parts[1].rstrip(':')
            
            # Extract MTU
            mtu = 0
            for j, part in enumerate(parts):
                if part == 'mtu':
                    mtu = int(parts[j + 1])
                    break
            
            # Extract flags
            flags = ""
            if 'LOOPBACK' in line:
                flags += "L"
            if '<' in line and 'UP' in line:
                flags += "RU"
            if 'BROADCAST' in line:
                flags += "B"
            if 'MULTICAST' in line:
                flags += "M"
            
            # Move to next line (link/ether or link/loopback)
            i += 1
            
            # Move to RX: line
            i += 1
            
            # Get RX stats (next line after RX:)
            i += 1
            if i < len(lines):
                rx_line = lines[i].strip()
                rx_parts = rx_line.split()
                rx_packets = int(rx_parts[1]) if len(rx_parts) > 1 else 0
                rx_errors = int(rx_parts[2]) if len(rx_parts) > 2 else 0
                rx_dropped = int(rx_parts[3]) if len(rx_parts) > 3 else 0
            
            # Move to TX: line
            i += 1
            
            # Get TX stats (next line after TX:)
            i += 1
            if i < len(lines):
                tx_line = lines[i].strip()
                tx_parts = tx_line.split()
                tx_packets = int(tx_parts[1]) if len(tx_parts) > 1 else 0
                tx_errors = int(tx_parts[2]) if len(tx_parts) > 2 else 0
                tx_dropped = int(tx_parts[3]) if len(tx_parts) > 3 else 0
            
            interfaces.append({
                'iface': iface,
                'mtu': mtu,
                'rx_packets': rx_packets,
                'rx_errors': rx_errors,
                'rx_dropped': rx_dropped,
                'tx_packets': tx_packets,
                'tx_errors': tx_errors,
                'tx_dropped': tx_dropped,
                'flags': flags
            })
        
        i += 1
    
    return interfaces

def print_netstat_format(interfaces):
    """Print interfaces in netstat -in format."""
    print("Kernel Interface table")
    print(f"{'Iface':<16} {'MTU':>5} {'RX-OK':>8} {'RX-ERR':>6} {'RX-DRP':>6} "
          f"{'RX-OVR':>6} {'TX-OK':>8} {'TX-ERR':>6} {'TX-DRP':>6} {'TX-OVR':>6} Flg")
    
    for iface in interfaces:
        print(f"{iface['iface']:<16} "
              f"{iface['mtu']:>5} "
              f"{iface['rx_packets']:>8} "
              f"{iface['rx_errors']:>6} "
              f"{iface['rx_dropped']:>6} "
              f"{'0':>6} "
              f"{iface['tx_packets']:>8} "
              f"{iface['tx_errors']:>6} "
              f"{iface['tx_dropped']:>6} "
              f"{'0':>6} "
              f"{iface['flags']}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 ip_to_netstat.py <input_file>", file=sys.stderr)
        print("   or: ip -s link | python3 ip_to_netstat.py -", file=sys.stderr)
        sys.exit(1)
    
    input_file = sys.argv[1]
    
    # Read input
    if input_file == '-':
        lines = sys.stdin.readlines()
    else:
        try:
            with open(input_file, 'r') as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"Error: File '{input_file}' not found", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)
    
    # Parse and print
    interfaces = parse_ip_link_output(lines)
    
    if not interfaces:
        print("Error: No interfaces found in input", file=sys.stderr)
        sys.exit(1)
    
    print_netstat_format(interfaces)

if __name__ == '__main__':
    main()
