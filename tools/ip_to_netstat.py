#!/usr/bin/env python3
"""
ip_to_netstat.py — convert `ip -s link` output to netstat -in column layout.

Usage: ip_to_netstat.py <ip-s-link-output-file>

The script reads the file produced by `ip -s link` and prints a table that
matches the column layout of `netstat -in`:

  Iface  MTU  RX-OK  RX-ERR  RX-DRP  RX-OVR  TX-OK  TX-ERR  TX-DRP  TX-OVR  Flg
"""

import re
import sys


def parse_ip_s_link(path):
    """Parse `ip -s link` output and return a list of interface dicts."""
    with open(path) as fh:
        text = fh.read()

    # Each interface block starts with a numbered line like:
    #   1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 ...
    blocks = re.split(r'(?=^\d+:)', text, flags=re.MULTILINE)

    interfaces = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue

        # Header line: index, name, flags, mtu
        header_m = re.match(
            r'^\d+:\s+(\S+?)(?:@\S+)?:\s+<([^>]*)>\s+mtu\s+(\d+)',
            block, re.MULTILINE
        )
        if not header_m:
            continue

        name  = header_m.group(1)
        flags = header_m.group(2).split(',')
        mtu   = header_m.group(3)

        # RX stats line: "    RX:  bytes  packets  errors  dropped  missed  mcast"
        # followed by values on the next line.
        rx_m = re.search(
            r'RX:\s+bytes\s+packets\s+errors\s+dropped.*?\n\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
            block
        )
        # TX stats line
        tx_m = re.search(
            r'TX:\s+bytes\s+packets\s+errors\s+dropped.*?\n\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)',
            block
        )

        rx_ok  = rx_m.group(2) if rx_m else '0'
        rx_err = rx_m.group(3) if rx_m else '0'
        rx_drp = rx_m.group(4) if rx_m else '0'

        tx_ok  = tx_m.group(2) if tx_m else '0'
        tx_err = tx_m.group(3) if tx_m else '0'
        tx_drp = tx_m.group(4) if tx_m else '0'

        # Build flags string similar to netstat (B=BROADCAST, L=LOOPBACK,
        # M=MULTICAST, R=RUNNING, U=UP)
        flg_map = {
            'UP':          'U',
            'LOOPBACK':    'L',
            'BROADCAST':   'B',
            'MULTICAST':   'M',
            'RUNNING':     'R',
            'POINTOPOINT': 'P',
            'PROMISC':     'N',
        }
        flg = ''.join(flg_map[f] for f in flg_map if f in flags)

        interfaces.append({
            'name':   name,
            'mtu':    mtu,
            'rx_ok':  rx_ok,
            'rx_err': rx_err,
            'rx_drp': rx_drp,
            'rx_ovr': '0',
            'tx_ok':  tx_ok,
            'tx_err': tx_err,
            'tx_drp': tx_drp,
            'tx_ovr': '0',
            'flg':    flg or 'U',
        })

    return interfaces


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: ip_to_netstat.py <ip-s-link-output-file>")

    interfaces = parse_ip_s_link(sys.argv[1])

    header = (
        f"{'Iface':<10} {'MTU':>6}  "
        f"{'RX-OK':>10} {'RX-ERR':>8} {'RX-DRP':>8} {'RX-OVR':>8}  "
        f"{'TX-OK':>10} {'TX-ERR':>8} {'TX-DRP':>8} {'TX-OVR':>8}  Flg"
    )
    print(header)

    for i in interfaces:
        print(
            f"{i['name']:<10} {i['mtu']:>6}  "
            f"{i['rx_ok']:>10} {i['rx_err']:>8} {i['rx_drp']:>8} {i['rx_ovr']:>8}  "
            f"{i['tx_ok']:>10} {i['tx_err']:>8} {i['tx_drp']:>8} {i['tx_ovr']:>8}  {i['flg']}"
        )


if __name__ == '__main__':
    main()
