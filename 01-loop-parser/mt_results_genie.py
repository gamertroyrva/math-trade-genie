#!/usr/bin/env python3
"""
Math Trade Results Genie
Translates cryptic math trade results into human-readable trade loops.

Usage:
  python mt_results_genie.py <results_file> <wants_file> [output_file]

If output_file is omitted, output goes to <results_stem>_loops.txt
in the same folder as the results file.
"""

import sys
import re
from pathlib import Path


def parse_official_names(wants_file):
    names = {}
    user_case = {}
    in_block = False

    with open(wants_file, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if "!BEGIN-OFFICIAL-NAMES" in line:
                in_block = True
                continue
            if "!END-OFFICIAL-NAMES" in line:
                break
            if not in_block:
                continue
            m = re.match(r'^(\S+)\s+==>.*?"([^"]+)"\s+\(from\s+([^)]+)\)', line)
            if m:
                names[m.group(1)] = m.group(2)
                user_case[m.group(3).strip().upper()] = m.group(3).strip()

    return names, user_case


def parse_trade_loops(results_file):
    with open(results_file, encoding="utf-8") as f:
        lines = f.readlines()

    total_trades = 0
    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        m = re.search(r"TRADE LOOPS \((\d+) total trades\)", line)
        if m:
            total_trades = int(m.group(1))
            start_idx = i + 1
        if start_idx is not None and "ITEM SUMMARY" in line:
            end_idx = i
            break

    if start_idx is None:
        raise ValueError("Could not find TRADE LOOPS section in: " + str(results_file))

    edge_re = re.compile(r"\(([^)]+)\)\s+(\S+)\s+receives\s+\(([^)]+)\)\s+(\S+)")

    loops = []
    current_loop = []

    for line in lines[start_idx:end_idx]:
        stripped = line.strip()
        if not stripped:
            if current_loop:
                loops.append(list(reversed(current_loop)))
                current_loop = []
        else:
            m = edge_re.match(stripped)
            if m:
                current_loop.append((m.group(3), m.group(4), m.group(1)))

    if current_loop:
        loops.append(list(reversed(current_loop)))

    return total_trades, loops


def format_output(total_trades, loops, names, user_case):
    num_loops = len(loops)
    loop_word = "loop" if num_loops == 1 else "loops"
    out = ["{} total trades · {} {}".format(total_trades, num_loops, loop_word)]

    for loop_idx, loop in enumerate(loops, start=1):
        num_edges = len(loop)
        trade_word = "trade" if num_edges == 1 else "trades"
        out.append("")
        out.append("Loop {} ({} {})".format(loop_idx, num_edges, trade_word))
        field_width = max(5, len(str(num_edges)) + 3)

        for edge_idx, (sender, item_id, receiver) in enumerate(loop, start=1):
            game     = names.get(item_id, "UNKNOWN:" + item_id)
            sender   = user_case.get(sender.upper(),   sender)
            receiver = user_case.get(receiver.upper(), receiver)
            num_str  = str(edge_idx).rjust(field_width)
            out.append("{}. {} -> [{}] -> {}".format(num_str, sender, game, receiver))

    return "\n".join(out) + "\n"


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    results_file = Path(sys.argv[1])
    wants_file   = Path(sys.argv[2])
    output_file  = Path(sys.argv[3]) if len(sys.argv) >= 4 else results_file.parent / (results_file.stem + "_loops.txt")

    print("Reading names from : " + str(wants_file))
    names, user_case = parse_official_names(wants_file)
    print("  {} item names loaded".format(len(names)))

    print("Reading loops from : " + str(results_file))
    total_trades, loops = parse_trade_loops(results_file)
    print("  {} total trades in {} loop(s)".format(total_trades, len(loops)))

    output = format_output(total_trades, loops, names, user_case)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(output)

    print("Output written to  : " + str(output_file))


if __name__ == "__main__":
    main()
