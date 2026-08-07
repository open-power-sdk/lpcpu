#!/usr/bin/env python3

import argparse
import re
import sys

HEADER_RE = re.compile(r'^\s*Netid\s+State\s+Recv-Q\s+Send-Q\s+Local Address:Port\s+Peer Address:Port\s*$')
WS_RE = re.compile(r'\s+')


def parse_ss_line(line):
    stripped = line.rstrip('\n')
    if not stripped.strip():
        return None
    if HEADER_RE.match(stripped):
        return {"type": "header", "raw": stripped}

    parts = WS_RE.split(stripped.strip())
    if len(parts) < 6:
        return {"type": "raw", "raw": stripped}

    return {
        "type": "row",
        "tool": "ss",
        "netid": parts[0],
        "state": parts[1],
        "recv_q": parts[2],
        "send_q": parts[3],
        "local": parts[-2],
        "peer": parts[-1],
        "raw": stripped,
    }


def parse_netstat_line(line):
    stripped = line.rstrip('\n')
    if not stripped.strip():
        return None

    if stripped.startswith("Active "):
        return {"type": "section", "raw": stripped}

    if stripped.startswith("Proto "):
        return {"type": "header", "raw": stripped}

    parts = WS_RE.split(stripped.strip())
    if len(parts) < 5:
        return {"type": "raw", "raw": stripped}

    proto = parts[0]

    if proto in ("tcp", "tcp4", "tcp6", "udp", "udp4", "udp6"):
        if len(parts) < 6:
            return {"type": "raw", "raw": stripped}
        return {
            "type": "row",
            "tool": "netstat",
            "netid": proto,
            "state": parts[-1],
            "recv_q": parts[1],
            "send_q": parts[2],
            "local": parts[3],
            "peer": parts[4],
            "raw": stripped,
        }

    if proto == "unix":
        if len(parts) < 6:
            return {"type": "raw", "raw": stripped}
        state = ""
        local = ""
        peer = ""

        if len(parts) >= 7:
            state = parts[4]
            peer = parts[5]
            if len(parts) > 6:
                local = " ".join(parts[6:])
        else:
            state = parts[4]
            peer = parts[5]

        return {
            "type": "row",
            "tool": "netstat",
            "netid": proto,
            "state": state,
            "recv_q": parts[1],
            "send_q": parts[2],
            "local": local if local else "*",
            "peer": peer,
            "raw": stripped,
        }

    return {"type": "raw", "raw": stripped}


def parse_file(path, mode):
    rows = []
    raw = []
    parser = parse_ss_line if mode == "ss" else parse_netstat_line

    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            parsed = parser(line)
            if parsed is None:
                continue
            if parsed["type"] == "row":
                rows.append(parsed)
            else:
                raw.append(parsed["raw"])
    return rows, raw


def sort_key(row):
    return (
        row["netid"],
        row["local"],
        row["peer"],
        row["state"],
        row["recv_q"],
        row["send_q"],
        row["raw"],
    )


def main():
    ap = argparse.ArgumentParser(description="Normalize and sort netstat -v or ss output")
    ap.add_argument("--mode", choices=["ss", "netstat"], required=True)
    ap.add_argument("input_file")
    args = ap.parse_args()

    rows, raw = parse_file(args.input_file, args.mode)

    print("# normalized_from=%s mode=%s" % (args.input_file, args.mode))
    for line in raw:
        print("# raw: %s" % line)

    print("Netid State Recv-Q Send-Q Local_Address:Port Peer_Address:Port")
    for row in sorted(rows, key=sort_key):
        print(
            "%s %s %s %s %s %s"
            % (
                row["netid"],
                row["state"],
                row["recv_q"],
                row["send_q"],
                row["local"],
                row["peer"],
            )
        )


if __name__ == "__main__":
    main()

# Made with Bob
