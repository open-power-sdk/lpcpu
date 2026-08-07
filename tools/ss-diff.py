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

        # Format: State  Recv-Q  Send-Q  Local Address:Port  Peer Address:Port
        parts = line.split()

        if len(parts) < 5:
            continue

        state  = parts[0]
        recv_q = parts[1]
        send_q = parts[2]
        local  = parts[3]
        peer   = parts[4]

        # Split address:port (rsplit handles IPv6 brackets correctly)
        if ':' in local:
            local_addr, local_port = local.rsplit(':', 1)
        else:
            local_addr, local_port = local, '*'

        if ':' in peer:
            peer_addr, peer_port = peer.rsplit(':', 1)
        else:
            peer_addr, peer_port = peer, '*'

        key = (local_addr, local_port, peer_addr, peer_port)
        sockets[key] = {
            'state':  state,
            'recv_q': recv_q,
            'send_q': send_q,
            'local':  local,
            'peer':   peer,
            'line':   line.rstrip(),
        }

    return sockets


def format_socket_line(marker, socket_info):
    """
    Format a socket line with proper spacing to match ss output format.

    marker: '[+]', '[-]', or '   ' (3 spaces for unchanged)
    socket_info: dictionary with socket information
    """
    state  = socket_info['state']
    recv_q = socket_info['recv_q']
    send_q = socket_info['send_q']
    local  = socket_info['local']
    peer   = socket_info['peer']

    # State(20) Recv-Q(24) Send-Q(24) Local(60) Peer(40)
    return f"{marker} {state:<17} {recv_q:>20} {send_q:>24} {local:>56} {peer:>40}"


def compare_sockets(file1, file2):
    """
    Compare two ss output files and print the differences with deltas.

    file1: before file
    file2: after file
    """
    sockets_before = parse_ss_output(file1)
    sockets_after  = parse_ss_output(file2)

    all_keys    = set(sockets_before.keys()) | set(sockets_after.keys())
    sorted_keys = sorted(all_keys, key=lambda k: (k[0], k[1], k[2], k[3]))

    # Header
    print(
        f"    {'State':<17} {'Recv-Q':>20} {'Send-Q':>24}"
        f" {'Local Address:Port':>56} {'Peer Address:Port':>40}"
    )

    for key in sorted_keys:
        in_before = key in sockets_before
        in_after  = key in sockets_after

        if in_before and in_after:
            # Present in both — show queue deltas (after - before)
            try:
                recv_delta = int(sockets_after[key]['recv_q']) - int(sockets_before[key]['recv_q'])
                send_delta = int(sockets_after[key]['send_q']) - int(sockets_before[key]['send_q'])
                delta_info = sockets_after[key].copy()
                delta_info['recv_q'] = str(recv_delta)
                delta_info['send_q'] = str(send_delta)
                print(format_socket_line("   ", delta_info))
            except ValueError:
                print(format_socket_line("   ", sockets_after[key]))

        elif in_after:
            # Added during profiling — show actual after values
            print(format_socket_line("[+]", sockets_after[key]))

        else:
            # Removed during profiling — show negative before values
            removed_info = sockets_before[key].copy()
            try:
                recv_val = int(removed_info['recv_q'])
                send_val = int(removed_info['send_q'])
                removed_info['recv_q'] = str(-recv_val) if recv_val != 0 else '0'
                removed_info['send_q'] = str(-send_val) if send_val != 0 else '0'
            except ValueError:
                removed_info['recv_q'] = '-' + removed_info['recv_q']
                removed_info['send_q'] = '-' + removed_info['send_q']
            print(format_socket_line("[-]", removed_info))


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

    compare_sockets(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
