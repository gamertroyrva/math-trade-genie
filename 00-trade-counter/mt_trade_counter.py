#!/usr/bin/env python3
"""
MT Trade Counter — Block 0 of Math Trade Genie
Counts trades per participant from the raw OLWLG results file,
validates counts against header totals, and produces a publishable list.

Usage:
  python mt_trade_counter.py <results_file> [output_file]

If output_file is omitted, output goes to <results_stem>_trade_counts.txt
in the same folder as the results file.
"""

import sys
import re
from collections import defaultdict
from pathlib import Path


# ── Parsing ───────────────────────────────────────────────────────────────────

def parse_results(results_file: Path):
    """Return (header_trades, header_traders, trade_lines) from the results file."""
    header_trades  = None
    header_traders = None
    trade_lines    = []
    in_summary     = False

    with open(results_file, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")

            if header_traders is None:
                m = re.search(r"\[\s*users trading\s*=\s*(\d+)\s*\]", line)
                if m:
                    header_traders = int(m.group(1))

            if header_trades is None:
                m = re.search(r"TRADE LOOPS \((\d+) total trades\)", line)
                if m:
                    header_trades = int(m.group(1))

            if "ITEM SUMMARY" in line and "total trades" in line:
                in_summary = True
                continue

            if in_summary:
                if "Results Checksum" in line:
                    break
                if "and sends to" in line:
                    trade_lines.append(line)

    return header_trades, header_traders, trade_lines


def extract_trader(line: str):
    """Return the trader name from the leading (NAME) token."""
    m = re.match(r"^\(([^)]+)\)", line.strip())
    return m.group(1) if m else None


# ── Validation ────────────────────────────────────────────────────────────────

def validate(header_trades, header_traders, trade_lines, counts):
    errors = []

    line_count = len(trade_lines)
    if line_count != header_trades:
        errors.append(
            f"  Trade line count mismatch: found {line_count} lines in ITEM SUMMARY, "
            f"expected {header_trades} from header."
        )

    distinct_traders = len(counts)
    if distinct_traders != header_traders:
        errors.append(
            f"  Trader count mismatch: found {distinct_traders} distinct traders, "
            f"expected {header_traders} from header."
        )

    total_from_counts = sum(counts.values())
    if total_from_counts != header_trades:
        errors.append(
            f"  Per-participant sum mismatch: counts sum to {total_from_counts}, "
            f"expected {header_trades} from header."
        )

    return errors


# ── Formatting ────────────────────────────────────────────────────────────────

def format_publishable_list(counts, header_trades, header_traders, checks_passed):
    lines = []
    for trader in sorted(counts, key=str.upper):
        n = counts[trader]
        word = "trade" if n == 1 else "trades"
        lines.append(f"{trader.upper()} — {n} {word}")

    lines.append("")
    lines.append("─" * 50)

    if checks_passed:
        lines.append(f"Total trades:   {header_trades}  ✓")
        lines.append(f"Total traders:  {header_traders}  ✓")
        lines.append("All three validation checks passed.")
    else:
        lines.append(f"Total trades (header):   {header_trades}")
        lines.append(f"Total traders (header):  {header_traders}")
        lines.append("NOTE: Validation failed — see errors above.")

    return "\n".join(lines)


ERROR_WARNING = (
    "This file exists because the numbers didn't add up. You're welcome — lesser\n"
    "pipelines would have let you publish this and embarrass yourself. Remember your\n"
    "2024 taxes before you even think about pasting this into the Discussion Thread."
)


def format_error_file(errors, counts, header_trades, header_traders):
    sections = []

    sections.append("VALIDATION ERRORS")
    sections.append("─" * 50)
    sections.extend(errors)

    sections.append("")
    sections.append("WOULD-BE PUBLISHABLE LIST (do not use)")
    sections.append("─" * 50)
    sections.append(format_publishable_list(counts, header_trades, header_traders, checks_passed=False))

    sections.append("")
    sections.append("─" * 50)
    sections.append(ERROR_WARNING)

    return "\n".join(sections)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    results_file = Path(sys.argv[1])
    if not results_file.exists():
        print(f"Error: results file not found: {results_file}")
        sys.exit(1)

    header_trades, header_traders, trade_lines = parse_results(results_file)

    if header_trades is None:
        print("Error: could not find 'TRADE LOOPS (N total trades)' in results file.")
        sys.exit(1)
    if header_traders is None:
        print("Error: could not find '[ users trading = N ]' in results file.")
        sys.exit(1)

    counts = defaultdict(int)
    for line in trade_lines:
        trader = extract_trader(line)
        if trader:
            counts[trader] += 1

    errors = validate(header_trades, header_traders, trade_lines, counts)

    stem = results_file.stem

    if errors:
        error_path = (
            Path(sys.argv[2]) if len(sys.argv) >= 3
            else results_file.parent / f"{stem}_trade_counts_error.txt"
        )
        error_path.write_text(
            format_error_file(errors, counts, header_trades, header_traders),
            encoding="utf-8"
        )
        print("VALIDATION FAILED")
        print("─" * 50)
        for e in errors:
            print(e)
        print(f"\nDiagnostic file written: {error_path}")
        sys.exit(1)

    out_path = (
        Path(sys.argv[2]) if len(sys.argv) >= 3
        else results_file.parent / f"{stem}_trade_counts.txt"
    )
    out_path.write_text(
        format_publishable_list(counts, header_trades, header_traders, checks_passed=True),
        encoding="utf-8"
    )
    print(f"Trade counts written: {out_path}")
    print(f"  {header_trades} trades across {header_traders} traders — all checks passed.")


if __name__ == "__main__":
    main()
