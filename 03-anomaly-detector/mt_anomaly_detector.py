#!/usr/bin/env python3
"""
MT Error Detector — Block 3 of Math Trade Genie
Identifies potentially unfair trades by estimating real-world game values.

Reads the loops .txt file produced by Block 1 (mt_results_genie.py) and reports
the Top N trades where the giver's item significantly exceeds what they receive
in real-world market value.

Usage:
  python mt_error_detector.py <loops_file> [--top N] [--output <path>] [--all]

Arguments:
  loops_file     Path to the loops .txt file (Block 1 output)
  --top N        Number of worst-delta trades to report (default: 10)
  --output PATH  Output file path (default: auto-named in outputs/)
  --all          QA mode: show every trade pair, not just the top N worst

Value sources (in priority order):
  1. Stated dollar amount for "Alt Name: $X ..." cash items (instant, free)
  2. Claude AI estimate via Anthropic API, batched for all unknown games in
     a single call (requires ANTHROPIC_API_KEY environment variable)
  3. Unknown — flagged in the report for manual review

Caching:
  Successful Claude valuations are cached in value_cache.json next to this
  script. Each game is only ever looked up once. The cache grows over time
  and API calls become increasingly rare.

Road map:
  BGG marketplace integration (requires BGG API app registration) will
  replace or supplement Claude estimates in a future version.
"""

import sys
import re
import json
import argparse
from pathlib import Path
from typing import Optional, Tuple

# ── Configuration ─────────────────────────────────────────────────────────────

TOP_N_DEFAULT = 10
CACHE_FILE    = Path(__file__).parent / "value_cache.json"
CLAUDE_MODEL  = "claude-haiku-4-5-20251001"


# ── Cache ─────────────────────────────────────────────────────────────────────

def load_cache() -> dict:
    if CACHE_FILE.exists():
        with open(CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_cache(cache: dict) -> None:
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


# ── Parsing ───────────────────────────────────────────────────────────────────

def parse_loops_file(filepath: Path) -> list:
    """
    Parse a loops .txt file (Block 1 output) into structured data.

    Returns a list of loops. Each loop is a list of (giver, item, receiver)
    tuples in order. Usernames may contain spaces.
    """
    loops = []
    current_loop = []

    loop_header_re = re.compile(r'^Loop \d+')
    # Non-greedy on giver and receiver to correctly handle multi-word usernames.
    edge_re = re.compile(r'^\s+\d+\.\s+(.+?)\s+->\s+\[(.+?)\]\s+->\s+(.+?)\s*$')

    with open(filepath, encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if loop_header_re.match(line):
                if current_loop:
                    loops.append(current_loop)
                current_loop = []
                continue
            m = edge_re.match(line)
            if m:
                current_loop.append((
                    m.group(1).strip(),
                    m.group(2).strip(),
                    m.group(3).strip()
                ))

    if current_loop:
        loops.append(current_loop)

    return loops


# ── Value Estimation ──────────────────────────────────────────────────────────

def parse_cash_value(item_name: str) -> Optional[float]:
    """
    Return the dollar amount if this is a cash alt-name item, else None.
    Handles: "Alt Name: $20 cash/PayPal/Venmo", "Alt Name: $5 Cash/...", etc.
    """
    if not item_name.lower().startswith("alt name"):
        return None
    m = re.search(r'\$(\d+(?:\.\d+)?)', item_name)
    return float(m.group(1)) if m else None


def claude_batch_estimate(game_names: list) -> dict:
    """
    Use Claude Haiku to estimate used secondhand market values for a list of
    board games. All games are sent in a single API call to minimize token use.

    Returns {game_name: (price_or_None, confidence_str)}
    where confidence_str is "high", "medium", or "low".

    Requires the ANTHROPIC_API_KEY environment variable to be set.
    """
    try:
        import anthropic
    except ImportError:
        print("  [error] 'anthropic' library not installed. Run: pip install anthropic")
        return {name: (None, "unknown") for name in game_names}

    games_list = "\n".join(f"- {name}" for name in game_names)

    prompt = f"""You are a board game pricing expert with deep knowledge of the \
secondhand board game market in the United States.

For each of the following board games, estimate the typical used market value \
in USD. Base your estimate on what the game typically sells for in good/very \
good condition on platforms like eBay, Facebook Marketplace, or the \
BoardGameGeek marketplace.

Return a JSON object where each key is the EXACT game name as provided and \
each value is an object with:
- "price": your best estimate as a number (e.g., 25.00), or null if you truly \
have no basis for an estimate
- "confidence": "high" if you know this game well and are very confident, \
"medium" if you have a reasonable idea, "low" if you are estimating with \
limited knowledge

Prefer making a "low" confidence estimate over returning null — even a rough \
estimate is more useful than nothing for detecting egregious value mismatches.

Games to value:
{games_list}

Return ONLY valid JSON. No other text, no markdown, no code fences."""

    try:
        client = anthropic.Anthropic()
        message = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = message.content[0].text.strip()

        # Strip markdown code fences if the model added them anyway
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        data = json.loads(response_text)

        result = {}
        for name in game_names:
            entry = data.get(name, {})
            if isinstance(entry, dict):
                price      = entry.get("price")
                confidence = entry.get("confidence", "low")
                result[name] = (float(price) if price is not None else None, confidence)
            else:
                result[name] = (None, "low")

        return result

    except json.JSONDecodeError as e:
        print(f"  [Claude response parse error] {e}")
        return {name: (None, "unknown") for name in game_names}
    except Exception as e:
        print(f"  [Claude API error] {type(e).__name__}: {e}")
        return {name: (None, "unknown") for name in game_names}


# ── Delta Computation ─────────────────────────────────────────────────────────

def compute_all_deltas(loops: list, cache: dict) -> list:
    """
    Walk every consecutive edge pair in every loop, including the wrap-around
    pair connecting the last edge back to the first.

    For each pair:
      - The connecting person RECEIVES the item on edge N
      - The connecting person GIVES the item on edge N+1
      - delta = value(received) - value(given)
      - Negative delta = giver overpays (the error we are hunting)

    Returns a flat list of delta record dicts.
    """
    # Collect all unique item names across all loops
    all_items = set()
    for loop in loops:
        for _giver, item, _receiver in loop:
            all_items.add(item)

    print(f"  Estimating values for {len(all_items)} unique item(s)...")

    values      = {}   # item -> (value, source, notes)
    needs_claude = []  # items that need a Claude API call

    # ── Pass 1: handle everything we can without an API call ──────────────────
    for item in sorted(all_items):

        # Cash alt-name items
        cash = parse_cash_value(item)
        if cash is not None:
            values[item] = (cash, "stated cash", "")
            print(f"    {item[:58]:<58}  ${cash:.2f}")
            continue

        # Non-cash alt-name items (accessories, promos, in-kind)
        if item.lower().startswith("alt name"):
            values[item] = (None, "unknown", "Non-cash alt-name item; no automatic valuation")
            print(f"    {item[:58]:<58}  unknown (non-cash alt name)")
            continue

        # Items explicitly outside BGG scope
        if "outside the scope of bgg" in item.lower():
            values[item] = (None, "unknown", "Item is outside BGG scope")
            print(f"    {item[:58]:<58}  unknown (outside BGG scope)")
            continue

        # Cache hit
        cache_key = f"claude_value:{item}"
        if cache_key in cache:
            cached = cache[cache_key]
            price  = cached["price"]
            conf   = cached["confidence"]
            values[item] = (price, f"Claude ({conf} confidence)", "cached")
            print(f"    {item[:58]:<58}  ${price:.2f}  [{conf}, cached]")
            continue

        # Everything else goes to Claude
        needs_claude.append(item)

    # ── Pass 2: batch Claude call for remaining items ─────────────────────────
    if needs_claude:
        print(f"\n  Calling Claude to value {len(needs_claude)} game(s) "
              f"(1 API call)...")
        claude_results = claude_batch_estimate(needs_claude)

        for item in needs_claude:
            price, confidence = claude_results.get(item, (None, "unknown"))

            if price is not None:
                values[item] = (price, f"Claude ({confidence} confidence)", "AI estimate")
                cache[f"claude_value:{item}"] = {"price": price, "confidence": confidence}
                print(f"    {item[:58]:<58}  ${price:.2f}  ({confidence})")
            else:
                values[item] = (None, f"Claude (could not estimate)", "")
                print(f"    {item[:58]:<58}  unknown")

    print()

    # ── Compute deltas ────────────────────────────────────────────────────────
    records = []
    for loop_num, loop in enumerate(loops, 1):
        n = len(loop)
        for i in range(n):
            recv_edge = loop[i]            # giver -> [item_recv] -> PERSON
            give_edge = loop[(i + 1) % n]  # PERSON -> [item_give] -> receiver

            person    = recv_edge[2]
            item_recv = recv_edge[1]
            item_give = give_edge[1]

            val_r, src_r, note_r = values[item_recv]
            val_g, src_g, note_g = values[item_give]

            if val_r is not None and val_g is not None:
                delta = round(val_r - val_g, 2)
                known = True
            else:
                delta = None
                known = False

            records.append({
                "loop_num":    loop_num,
                "edge_index":  i + 1,
                "wrap":        (i == n - 1),
                "person":      person,
                "item_recv":   item_recv,
                "val_recv":    val_r,
                "src_recv":    src_r,
                "note_recv":   note_r,
                "item_give":   item_give,
                "val_give":    val_g,
                "src_give":    src_g,
                "note_give":   note_g,
                "delta":       delta,
                "delta_known": known,
            })

    return records


# ── Report Formatting ─────────────────────────────────────────────────────────

def _format_summary(records: list, W: int) -> list:
    """Build the SUMMARY section lines (no trailing = — caller appends it)."""
    total_pairs       = len(records)
    evaluated         = [r for r in records if r["delta_known"]]
    unevaluated_count = total_pairs - len(evaluated)

    overpaying     = [r for r in evaluated if r["delta"] < 0]
    favorable      = [r for r in evaluated if r["delta"] > 0]
    even           = [r for r in evaluated if r["delta"] == 0]

    total_overpaid = round(sum(abs(r["delta"]) for r in overpaying), 2)
    total_surplus  = round(sum(r["delta"]      for r in favorable),  2)
    discrepancy    = round(abs(total_overpaid - total_surplus),       2)
    balanced       = discrepancy < 0.01

    out = []
    out.append("=" * W)
    out.append("SUMMARY")
    out.append("=" * W)
    out.append(f"  Total trade pairs            : {total_pairs}")
    out.append(f"    Evaluated                  : {len(evaluated)}")
    out.append(f"      Overpaying               : {len(overpaying):<4}  total overpaid  : ${total_overpaid:.2f}")
    out.append(f"      Favorable                : {len(favorable):<4}  total surplus   : ${total_surplus:.2f}")
    out.append(f"      Even                     : {len(even)}")
    out.append(f"    Unevaluated                : {unevaluated_count}    (one or both item values unknown)")
    out.append("")

    if balanced:
        out.append(f"  Closed system check          : BALANCED  ✓")
        out.append(f"  (${total_overpaid:.2f} overpaid = ${total_surplus:.2f} surplus — every dollar accounted for)")
    else:
        out.append(f"  Closed system check          : IMBALANCED  ✗  (discrepancy: ${discrepancy:.2f})")
        out.append(f"  (${total_overpaid:.2f} overpaid ≠ ${total_surplus:.2f} surplus)")

    out.append("")
    out.append(f"  Community value harvested    : ${total_surplus:.2f}")

    return out

def _fmtv(v: Optional[float]) -> str:
    return f"${v:.2f}" if v is not None else "UNKNOWN"


def _render_pair(out: list, rank: Optional[int], r: dict) -> None:
    """Append one trade-pair block to the output list."""
    delta_abs = abs(r["delta"]) if r["delta"] is not None else None
    if r["delta"] is None:
        verdict = "delta unknown — see incomplete section"
    elif r["delta"] < 0:
        verdict = f"{r['person']} overpays by ${delta_abs:.2f}"
    elif r["delta"] == 0:
        verdict = f"Even trade for {r['person']}"
    else:
        verdict = f"{r['person']} receives ${delta_abs:.2f} surplus (favorable)"

    wrap_tag = "  [wrap-around]" if r["wrap"] else ""
    rank_tag = f"  #{rank}" if rank is not None else "  "
    out.append(f"{rank_tag}  Loop {r['loop_num']}, Edge {r['edge_index']}{wrap_tag}")
    out.append(f"       Person   : {r['person']}")
    out.append(f"       Receives : [{r['item_recv']}]")
    out.append(f"                  Value: {_fmtv(r['val_recv'])}  ({r['src_recv']})")
    if r["note_recv"]:
        out.append(f"                  Note : {r['note_recv']}")
    out.append(f"       Gives    : [{r['item_give']}]")
    out.append(f"                  Value: {_fmtv(r['val_give'])}  ({r['src_give']})")
    if r["note_give"]:
        out.append(f"                  Note : {r['note_give']}")
    out.append(f"       Verdict  : {verdict}")
    out.append("")


def format_report(records: list, top_n: int, loops_file: Path,
                  show_all: bool = False) -> str:
    """
    Format the plain-text error report.

    show_all=False (default / production mode):
      Shows the top_n worst-delta trade pairs plus the incomplete-data section.

    show_all=True (QA mode):
      Shows every trade pair, sorted worst delta first, so you can review the
      full picture before releasing results. Incomplete pairs appear at the end.
    """
    known   = sorted([r for r in records if r["delta_known"]], key=lambda r: r["delta"])
    unknown = [r for r in records if not r["delta_known"]]

    W = 70
    out = []

    # ── Header ────────────────────────────────────────────────────────────────
    out.append("=" * W)
    title = "MATH TRADE GENIE — ANOMALY DETECTOR REPORT"
    if show_all:
        title += "  [QA MODE — ALL PAIRS]"
    out.append(title)
    out.append("=" * W)
    out.append(f"Source file  : {loops_file.name}")
    out.append(f"Total pairs  : {len(records)}")
    out.append(f"  Valued     : {len(known)}")
    out.append(f"  Incomplete : {len(unknown)}")
    if show_all:
        out.append(f"Mode         : QA (all {len(known)} valued pairs shown)")
    else:
        out.append(f"Top N shown  : {top_n}")
    out.append("")

    # ── Valued pairs section ──────────────────────────────────────────────────
    if show_all:
        section_title = f"ALL {len(known)} VALUED TRADE PAIRS  (worst delta first)"
        section_note  = ("Complete listing for QA review. Overpayors appear first; "
                         "favorable trades appear last.")
    else:
        section_title = f"TOP {top_n} WORST-VALUE TRADES"
        section_note  = "Ranked by how much the giver overpays (most egregious first)."

    out.append(section_title)
    out.append(section_note)
    out.append("Negative delta = giver receives less than they give.")
    out.append("-" * W)
    out.append("")

    display_known = known if show_all else known[:top_n]

    if not display_known:
        out.append("  No fully-valued trade pairs found.")
        out.append("")
    else:
        for rank, r in enumerate(display_known, 1):
            _render_pair(out, rank, r)

    # ── Incomplete data section ───────────────────────────────────────────────
    if unknown:
        out.append("")
        out.append(f"TRADES WITH INCOMPLETE VALUE DATA  ({len(unknown)} pairs)")
        out.append("One or both sides could not be valued automatically.")
        out.append("Review manually if either item looks like it could be high-value.")
        out.append("-" * W)
        out.append("")
        for r in unknown:
            wrap_tag = " [wrap]" if r["wrap"] else ""
            out.append(f"  Loop {r['loop_num']}, Edge {r['edge_index']}{wrap_tag} — {r['person']}")
            out.append(f"    Receives : [{r['item_recv']}]")
            out.append(f"               {_fmtv(r['val_recv'])}  ({r['src_recv']})")
            if r["note_recv"]:
                out.append(f"               {r['note_recv']}")
            out.append(f"    Gives    : [{r['item_give']}]")
            out.append(f"               {_fmtv(r['val_give'])}  ({r['src_give']})")
            if r["note_give"]:
                out.append(f"               {r['note_give']}")
            out.append("")

    out.extend(_format_summary(records, W))
    out.append("=" * W)
    out.append("END OF REPORT")
    out.append("=" * W)

    return "\n".join(out) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="MT Error Detector — identify unfair math trade pairs by real-world value"
    )
    parser.add_argument(
        "loops_file",
        help="Loops .txt file produced by Block 1 (mt_results_genie.py)"
    )
    parser.add_argument(
        "--top", type=int, default=TOP_N_DEFAULT, metavar="N",
        help=f"Number of worst trades to report (default: {TOP_N_DEFAULT})"
    )
    parser.add_argument(
        "--output",
        help="Output report file path (default: auto-named in outputs/)"
    )
    parser.add_argument(
        "--all", dest="show_all", action="store_true",
        help="QA mode: show every trade pair, not just the top N worst"
    )
    args = parser.parse_args()

    loops_file = Path(args.loops_file)
    if not loops_file.exists():
        sys.exit(f"Error: File not found: {loops_file}")

    if args.output:
        output_file = Path(args.output)
    else:
        suffix = "_qa_report.txt" if args.show_all else "_anomaly_report.txt"
        output_file = loops_file.parent / (loops_file.stem + suffix)

    mode_label = "QA (all pairs)" if args.show_all else f"Top {args.top}"

    print("=" * 60)
    print("Math Trade Genie — Anomaly Detector  (Block 3)")
    print("=" * 60)
    print(f"  Loops file : {loops_file}")
    print(f"  Report out : {output_file}")
    print(f"  Mode       : {mode_label}")
    print()

    cache = load_cache()
    cached_games = sum(1 for k in cache if k.startswith("claude_value:"))
    print(f"Value cache: {cached_games} game(s) already valued")
    print()

    print("Parsing loops file...")
    loops = parse_loops_file(loops_file)
    total_edges = sum(len(lp) for lp in loops)
    print(f"  {len(loops)} loop(s), {total_edges} edge(s), "
          f"{total_edges} trade pairs to evaluate")
    print()

    print("Estimating item values...")
    records = compute_all_deltas(loops, cache)

    save_cache(cache)
    cached_games_after = sum(1 for k in cache if k.startswith("claude_value:"))
    print(f"Value cache saved: {cached_games_after} game(s) total  →  {CACHE_FILE.name}")
    print()

    report = format_report(records, args.top, loops_file, show_all=args.show_all)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(report, encoding="utf-8")

    known_count   = sum(1 for r in records if r["delta_known"])
    unknown_count = sum(1 for r in records if not r["delta_known"])
    print(f"Report written to: {output_file}")
    print(f"  Valued pairs    : {known_count}")
    print(f"  Incomplete pairs: {unknown_count}")


if __name__ == "__main__":
    main()
