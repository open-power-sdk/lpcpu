#!/usr/bin/env python3

"""
ss-diff.py - Compare two ss -lt socket snapshots with delta calculations

This script compares two ss -lt output files and shows:
- Sockets that were added (marked with [+]) - shows original values
- Sockets that were removed (marked with [-]) - shows negative values
- Sockets that remained (no marker) - shows delta (after - before)

For Recv-Q and Send-Q columns:
- Unchanged sockets: Shows the difference (delta) between before and after
- New sockets: Shows the actual values from the after file
- Removed sockets: Shows negative values from the before file

Sockets are matched by their unique identifier: Local Address:Port + Peer Address:Port
"""

import sys
import re
from collections import OrderedDict


def parse_ss_output(filename):
    """
    Parse ss -lt output file and return a dictionary of sockets.
    
    Key: (local_addr, local_port, peer_addr, peer_port)
    Value: (state, recv_q, send_q, full_line)
    """
    sockets = OrderedDict()
    
    try:
        with open(filename, 'r') as f:
            lines = f.readlines()
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file '{filename}': {e}", file=sys.stderr)
        sys.exit(1)
    
    # Skip header line
    if not lines:
        return sockets
    
    header_found = False
    for line in lines:
        # Skip header
        if 'State' in line and 'Recv-Q' in line and 'Send-Q' in line:
            header_found = True
            continue
        
        if not header_found:
            continue
            
        # Skip empty lines
        if not line.strip():
            continue
        
        # Parse socket line
        # Format: State  Recv-Q  Send-Q  Local Address:Port  Peer Address:Port
        parts = line.split()
        
        if len(parts) < 5:
            continue
        
        state = parts[0]
        recv_q = parts[1]
        send_q = parts[2]
        local = parts[3]
        peer = parts[4]
        
        # Split address:port
        if ':' in local:
            local_parts = local.rsplit(':', 1)
            local_addr = local_parts[0]
            local_port = local_parts[1] if len(local_parts) > 1 else '*'
        else:
            local_addr = local
            local_port = '*'
        
        if ':' in peer:
            peer_parts = peer.rsplit(':', 1)
            peer_addr = peer_parts[0]
            peer_port = peer_parts[1] if len(peer_parts) > 1 else '*'
        else:
            peer_addr = peer
            peer_port = '*'
        
        # Create unique key
        key = (local_addr, local_port, peer_addr, peer_port)
        
        # Store socket info
        sockets[key] = {
            'state': state,
            'recv_q': recv_q,
            'send_q': send_q,
            'local': local,
            'peer': peer,
            'line': line.rstrip()
        }
    
    return sockets


def format_socket_line(marker, socket_info):
    """
    Format a socket line with proper spacing to match ss output format.
    
    marker: '[+]', '[-]', or '   ' (3 spaces for unchanged)
    socket_info: dictionary with socket information
    """
    state = socket_info['state']
    recv_q = socket_info['recv_q']
    send_q = socket_info['send_q']
    local = socket_info['local']
    peer = socket_info['peer']
    
    # Format with consistent column widths matching ss output
    # State(20) Recv-Q(24) Send-Q(24) Local(60) Peer(40)
    line = f"{marker} {state:<17} {recv_q:>20} {send_q:>24} {local:>56} {peer:>40}"
    
    return line


def compare_sockets(file1, file2):
    """
    Compare two ss output files and print the differences with deltas.
    
    file1: before file
    file2: after file
    """
    sockets_before = parse_ss_output(file1)
    sockets_after = parse_ss_output(file2)
    
    # Get all unique socket keys
    all_keys = set(sockets_before.keys()) | set(sockets_after.keys())
    
    # Sort keys for consistent output
    sorted_keys = sorted(all_keys, key=lambda k: (k[0], k[1], k[2], k[3]))
    
    # Print header
    print(f"    {'State':<17} {'Recv-Q':>20} {'Send-Q':>24} {'Local Address:Port':>56} {'Peer Address:Port':>40}")
    
    # Compare and print
    for key in sorted_keys:
        in_before = key in sockets_before
        in_after = key in sockets_after
        
        if in_before and in_after:
            # Socket exists in both - calculate deltas (after - before)
            try:
                recv_q_before = int(sockets_before[key]['recv_q'])
                recv_q_after = int(sockets_after[key]['recv_q'])
                send_q_before = int(sockets_before[key]['send_q'])
                send_q_after = int(sockets_after[key]['send_q'])
                
                recv_q_delta = recv_q_after - recv_q_before
                send_q_delta = send_q_after - send_q_before
                
                # Create modified socket info with deltas
                delta_info = sockets_after[key].copy()
                delta_info['recv_q'] = str(recv_q_delta)
                delta_info['send_q'] = str(send_q_delta)
                
                marker = "   "  # 3 spaces for unchanged socket
                print(format_socket_line(marker, delta_info))
            except ValueError:
                # If conversion fails, show original values
                marker = "   "
                print(format_socket_line(marker, sockets_after[key]))
                
        elif in_after and not in_before:
            # Socket added - show original values from after file
            marker = "[+]"
            print(format_socket_line(marker, sockets_after[key]))
            
        elif in_before and not in_after:
            # Socket removed - show negative values from before file
            try:
                removed_info = sockets_before[key].copy()
                recv_q_val = int(removed_info['recv_q'])
                send_q_val = int(removed_info['send_q'])
                
                # Make values negative to indicate removal
                removed_info['recv_q'] = str(-recv_q_val) if recv_q_val != 0 else '0'
                removed_info['send_q'] = str(-send_q_val) if send_q_val != 0 else '0'
                
                marker = "[-]"
                print(format_socket_line(marker, removed_info))
            except ValueError:
                # If conversion fails, just prefix with minus
                removed_info = sockets_before[key].copy()
                removed_info['recv_q'] = '-' + removed_info['recv_q']
                removed_info['send_q'] = '-' + removed_info['send_q']
                marker = "[-]"
                print(format_socket_line(marker, removed_info))


def main():
    if len(sys.argv) != 3:
        print("Usage: ss-diff.py <before-file> <after-file>", file=sys.stderr)
        print("", file=sys.stderr)
        print("Compare two ss -lt output files and show differences with deltas:", file=sys.stderr)
        print("  [+] = Socket added (shows actual values)", file=sys.stderr)
        print("  [-] = Socket removed (shows negative values)", file=sys.stderr)
        print("  (no marker) = Socket unchanged (shows delta: after - before)", file=sys.stderr)
        print("", file=sys.stderr)
        print("For Recv-Q and Send-Q columns:", file=sys.stderr)
        print("  - Positive delta: value increased", file=sys.stderr)
        print("  - Negative delta: value decreased", file=sys.stderr)
        print("  - Zero: no change", file=sys.stderr)
        sys.exit(1)
    
    file_before = sys.argv[1]
    file_after = sys.argv[2]
    
    compare_sockets(file_before, file_after)


if __name__ == "__main__":
    main()

# Made with Bob