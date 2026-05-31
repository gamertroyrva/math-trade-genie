#!/usr/bin/env python3
"""
Math Trade Results Genie — HTML Visualizer (Chunk 2)
Converts a loops .txt file (output of mt_results_genie.py) into a
polished, self-contained HTML visualization page.

Usage:
  python mt_loops_to_html.py <loops_file> [output_file]
                             [--title "2025 End of Summer Math Trade"]
                             [--subtitle "BoardGameGeek · Richmond VA · No-Ship"]

If output_file is omitted, the HTML is written to <loops_stem>_visualization.html
in the same folder as the loops file.
"""

import sys
import re
import json
import argparse
from pathlib import Path


# ── PARSING ───────────────────────────────────────────────────────────────────

def parse_loops_file(path):
    """
    Parse a loops .txt file produced by mt_results_genie.py.
    Returns (total_trades, loops) where loops is a list of lists of
    [sender, game_name, receiver] triples.
    """
    with open(path, encoding="utf-8") as f:
        lines = f.readlines()

    total_trades = 0
    if lines:
        m = re.match(r"(\d+) total trades", lines[0].strip())
        if m:
            total_trades = int(m.group(1))

    loops = []
    current = []
    trade_re = re.compile(r"^\s+\d+\.\s+(.+?)\s+->\s+\[(.+?)\]\s+->\s+(.+?)\s*$")

    for line in lines[1:]:
        stripped = line.strip()
        if re.match(r"^Loop \d+", stripped):
            if current:
                loops.append(current)
                current = []
        else:
            m2 = trade_re.match(line)
            if m2:
                current.append([m2.group(1), m2.group(2), m2.group(3)])

    if current:
        loops.append(current)

    return total_trades, loops


def count_participants(loops):
    """Count unique usernames across all trades."""
    users = set()
    for loop in loops:
        for trade in loop:
            users.add(trade[0])
            users.add(trade[2])
    return len(users)


def derive_title(path):
    """Try to make a readable title from the filename."""
    stem = path.stem  # e.g. "results_2025_end-of-summer_loops"
    stem = re.sub(r"_loops$", "", stem)
    stem = re.sub(r"^results_", "", stem)
    stem = stem.replace("_", " ").replace("-", " ")
    words = stem.split()
    titled = " ".join(w.capitalize() for w in words)
    if "math trade" not in titled.lower():
        titled += " Math Trade"
    return titled


# ── HTML GENERATION ───────────────────────────────────────────────────────────

def build_loops_js(sorted_loops):
    """Build the LOOPS JavaScript constant with sequential numbers."""
    lines = ["const LOOPS = ["]
    for i, trades in enumerate(sorted_loops, start=1):
        trade_items = ",\n".join(
            "    " + json.dumps(t, ensure_ascii=False) for t in trades
        )
        lines.append(f"  {{ n: {i}, trades: [\n{trade_items}\n  ]}},")
    lines.append("];")
    return "\n".join(lines)


def _esc(s):
    """Escape HTML special characters."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def generate_html(page_title, eyebrow, cover_title, stats_line, loops_js, max_loop_size):
    html = HTML_TEMPLATE
    html = html.replace("%%PAGE_TITLE%%", _esc(page_title))
    html = html.replace("%%COVER_EYEBROW%%", _esc(eyebrow))
    html = html.replace("%%COVER_TITLE%%", _esc(cover_title))
    html = html.replace("%%COVER_STATS%%", stats_line)
    html = html.replace("%%LOOPS_DATA%%", loops_js)
    html = html.replace("%%MAX_LOOP_SIZE%%", str(max_loop_size))
    return html


# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate HTML visualization from math trade loops file.")
    parser.add_argument("loops_file", help="Path to the loops .txt file")
    parser.add_argument("output_file", nargs="?", help="Output HTML path (optional)")
    parser.add_argument("--title", default="",
                        help='Page and cover title, e.g. "2025 End of Summer Math Trade"')
    parser.add_argument("--subtitle", default="BoardGameGeek Math Trade",
                        help='Eyebrow subtitle, e.g. "BoardGameGeek · Richmond VA · No-Ship"')
    args = parser.parse_args()

    loops_path = Path(args.loops_file)
    if not loops_path.exists():
        print(f"Error: File not found: {loops_path}", file=sys.stderr)
        sys.exit(1)

    stem = loops_path.stem.replace("_loops", "")
    output_path = Path(args.output_file) if args.output_file else \
        loops_path.parent / (stem + "_visualization.html")

    print(f"Parsing loops from : {loops_path}")
    total_trades, loops = parse_loops_file(loops_path)
    print(f"  {total_trades} total trades in {len(loops)} loop(s)")

    num_participants = count_participants(loops)
    title = args.title if args.title else derive_title(loops_path)

    # Sort loops smallest -> largest; sequential numbering follows position
    sorted_loops = sorted(loops, key=lambda l: len(l))
    max_loop_size = max(len(l) for l in sorted_loops) if sorted_loops else 1

    loops_js = build_loops_js(sorted_loops)

    stats_line = (
        f"{total_trades} total trades &nbsp;&middot;&nbsp; "
        f"{len(loops)} loops &nbsp;&middot;&nbsp; "
        f"{num_participants} participants"
    )

    html = generate_html(
        page_title=title + " — Loop Results",
        eyebrow=args.subtitle,
        cover_title=title,
        stats_line=stats_line,
        loops_js=loops_js,
        max_loop_size=max_loop_size,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"HTML written to    : {output_path}")


# ── HTML TEMPLATE ─────────────────────────────────────────────────────────────

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%%PAGE_TITLE%%</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;600;700&family=JetBrains+Mono:wght@300;400;500&display=swap');

  :root {
    --bg:      #0a0c10;
    --bg2:     #111318;
    --bg3:     #181c24;
    --gold:    #c8a84b;
    --gold2:   #e8d08a;
    --teal:    #3db8c0;
    --rose:    #c05a6a;
    --muted:   #4a5060;
    --text:    #e2ddd4;
    --dim:     #8a8478;
    --border:  #222630;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  html { scroll-behavior: smooth; }

  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'JetBrains Mono', monospace;
    font-weight: 300;
    line-height: 1.6;
    overflow-x: hidden;
  }

  /* COVER */
  #cover {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 40px 60px;
    position: relative;
    overflow: hidden;
  }

  #cover::before {
    content: '';
    position: absolute;
    inset: 0;
    background:
      radial-gradient(ellipse 70% 50% at 15% 20%, rgba(200,168,75,0.06) 0%, transparent 60%),
      radial-gradient(ellipse 60% 50% at 85% 80%, rgba(61,184,192,0.05) 0%, transparent 60%);
    pointer-events: none;
  }

  .cover-eyebrow {
    font-size: 15px;
    letter-spacing: 0.3em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 24px;
    opacity: 0.7;
  }

  .cover-title {
    font-family: 'Cormorant Garamond', serif;
    font-size: clamp(36px, 6vw, 72px);
    font-weight: 700;
    line-height: 1.0;
    text-align: center;
    margin-bottom: 8px;
    color: var(--gold2);
    letter-spacing: -0.01em;
  }

  .cover-sub {
    font-size: 14px;
    color: var(--dim);
    letter-spacing: 0.15em;
    margin-bottom: 80px;
  }

  .cover-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 24px;
    justify-content: center;
    align-items: center;
    max-width: 900px;
    margin-bottom: 60px;
  }

  .cover-cell {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    opacity: 0.85;
    transition: opacity 0.2s, transform 0.2s;
  }

  .cover-cell:hover { opacity: 1; transform: scale(1.05); }

  .cover-cell-label {
    font-size: 9px;
    letter-spacing: 0.15em;
    color: var(--dim);
    text-transform: uppercase;
  }

  .scroll-hint {
    font-size: 13px;
    letter-spacing: 0.2em;
    color: var(--muted);
    text-transform: uppercase;
    animation: pulse 2.5s ease-in-out infinite;
  }

  @keyframes pulse { 0%,100%{opacity:0.4} 50%{opacity:1} }

  /* DIVIDER */
  .divider {
    width: 100%;
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--border), transparent);
    margin: 0;
  }

  /* LOOP SECTIONS */
  .loop-section {
    padding: 80px 40px;
    max-width: 1000px;
    margin: 0 auto;
    position: relative;
  }

  .loop-header {
    display: flex;
    align-items: baseline;
    gap: 20px;
    margin-bottom: 20px;
    padding-bottom: 20px;
    border-bottom: 1px solid var(--border);
  }

  .loop-num {
    font-family: 'Cormorant Garamond', serif;
    font-size: 64px;
    font-weight: 700;
    color: var(--border);
    line-height: 1;
    letter-spacing: -0.02em;
    user-select: none;
  }

  .loop-name {
    font-family: 'Cormorant Garamond', serif;
    font-size: 28px;
    font-weight: 600;
    color: var(--gold2);
  }

  .loop-meta {
    font-size: 10px;
    letter-spacing: 0.2em;
    color: var(--dim);
    text-transform: uppercase;
  }

  .loop-badge {
    margin-left: auto;
    font-size: 9px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--teal);
    border: 1px solid var(--teal);
    padding: 4px 10px;
    opacity: 0.7;
  }

  /* CIRCLE DIAGRAM */
  .diagram-wrap {
    display: flex;
    justify-content: center;
    overflow: visible;
  }

  .diagram-wrap svg { overflow: visible; }

  /* TEXT LIST */
  .trade-list {
    display: flex;
    flex-direction: column;
    gap: 0;
  }

  .trade-row {
    display: grid;
    grid-template-columns: 40px 1fr 2fr 1fr;
    gap: 16px;
    align-items: center;
    padding: 14px 0;
    border-bottom: 1px solid var(--border);
    transition: background 0.15s;
  }

  .trade-row:hover { background: rgba(255,255,255,0.02); }

  .trade-idx {
    font-size: 10px;
    color: var(--muted);
    text-align: right;
  }

  .trade-giver {
    font-size: 12px;
    color: var(--gold);
    font-weight: 500;
  }

  .trade-game {
    font-family: 'Cormorant Garamond', serif;
    font-size: 15px;
    font-weight: 400;
    color: var(--text);
    font-style: italic;
  }

  .trade-receiver {
    font-size: 12px;
    color: var(--teal);
    font-weight: 500;
  }
</style>
</head>
<body>

<div id="cover">
  <div class="cover-eyebrow">%%COVER_EYEBROW%%</div>
  <h1 class="cover-title">%%COVER_TITLE%%</h1>
  <div class="cover-sub">%%COVER_STATS%%</div>
  <div class="cover-grid" id="coverGrid"></div>
  <div class="scroll-hint">&#8595; &nbsp; scroll to explore each loop &nbsp; &#8595;</div>
</div>

<div class="divider"></div>
<div id="loopsWrapper"></div>

<script>
%%LOOPS_DATA%%

// LOOPS is already sorted smallest-to-largest and numbered sequentially (1, 2, 3...)
// by the generator script. No re-sort or re-numbering needed.

const MAX_LOOP_SIZE = %%MAX_LOOP_SIZE%%;

const PALETTE = [
  '#c8a84b','#3db8c0','#c05a6a','#7a9e6a','#8b7ab8',
  '#c88848','#4a9ab8','#b87a8a','#6a9e88','#a87ab8',
  '#b8a84b','#5abcc0'
];

function nodeColor(idx) { return PALETTE[idx % PALETTE.length]; }
function isCircle(loop) { return loop.trades.length <= 20; }
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── COVER THUMBNAILS ─────────────────────────────────────────────────────────

function makeCoverCircle(loop) {
  const T = loop.trades.length;
  const minSz = 50, maxSz = 155;
  const sz = Math.round(minSz + (T / MAX_LOOP_SIZE) * (maxSz - minSz));
  const R = sz / 2 - 6;
  const cx = sz / 2, cy = sz / 2;
  const nr = Math.max(2, Math.round(R * 0.12));
  const angles = loop.trades.map((_, i) => (2 * Math.PI * i / T) - Math.PI / 2);
  const pts = angles.map(a => ({ x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) }));

  let parts = [`<svg width="${sz}" height="${sz}" viewBox="0 0 ${sz} ${sz}">`];
  for (let i = 0; i < T; i++) {
    const next = (i + 1) % T;
    let da = angles[next] - angles[i];
    if (da < 0) da += 2 * Math.PI;
    const largeArc = da > Math.PI ? 1 : 0;
    const x1 = cx + R * Math.cos(angles[i]);
    const y1 = cy + R * Math.sin(angles[i]);
    const x2 = cx + R * Math.cos(angles[next]);
    const y2 = cy + R * Math.sin(angles[next]);
    parts.push(`<path d="M ${x1.toFixed(1)} ${y1.toFixed(1)} A ${R} ${R} 0 ${largeArc} 1 ${x2.toFixed(1)} ${y2.toFixed(1)}" fill="none" stroke="${nodeColor(i)}" stroke-width="1" opacity="0.5"/>`);
  }
  for (let i = 0; i < T; i++) {
    parts.push(`<circle cx="${pts[i].x.toFixed(1)}" cy="${pts[i].y.toFixed(1)}" r="${nr}" fill="${nodeColor(i)}" opacity="0.9"/>`);
  }
  parts.push('</svg>');
  return parts.join('');
}

// ── FULL CIRCLE DIAGRAM ───────────────────────────────────────────────────────

function makeCircleDiagram(loop) {
  const T = loop.trades.length;
  const labelSpace = 140;
  const minR = 120, maxR = 280;
  const R = Math.min(maxR, Math.max(minR, T * 16));
  const sz = (R + labelSpace) * 2;
  const cx = sz / 2, cy = sz / 2;
  const nodeR = Math.max(6, Math.min(14, Math.floor(R * 0.06)));
  const angles = loop.trades.map((_, i) => (2 * Math.PI * i / T) - Math.PI / 2);
  const pts = angles.map(a => ({ x: cx + R * Math.cos(a), y: cy + R * Math.sin(a) }));
  const markerId = `arr${loop.n}`;

  let parts = [];
  parts.push(`<svg width="100%" viewBox="0 0 ${sz} ${sz}" style="max-width:${sz}px">`);
  parts.push(`<defs><marker id="${markerId}" markerUnits="userSpaceOnUse" markerWidth="12" markerHeight="8" refX="12" refY="4" orient="auto"><polygon points="0 0, 12 4, 0 8" fill="#cccccc" opacity="0.9"/></marker></defs>`);

  for (let i = 0; i < T; i++) {
    const next = (i + 1) % T;
    let da = angles[next] - angles[i];
    if (da < 0) da += 2 * Math.PI;
    const largeArc = da > Math.PI ? 1 : 0;
    const clearAngle = Math.asin(Math.min(0.99, (nodeR + 4) / R));
    const x1 = (cx + R * Math.cos(angles[i] + clearAngle)).toFixed(1);
    const y1 = (cy + R * Math.sin(angles[i] + clearAngle)).toFixed(1);
    const x2 = (cx + R * Math.cos(angles[next] - clearAngle)).toFixed(1);
    const y2 = (cy + R * Math.sin(angles[next] - clearAngle)).toFixed(1);
    parts.push(`<path d="M ${x1} ${y1} A ${R} ${R} 0 ${largeArc} 1 ${x2} ${y2}" fill="none" stroke="${nodeColor(i)}" stroke-width="1.5" opacity="0.6" marker-end="url(#${markerId})"/>`);
  }

  for (let i = 0; i < T; i++) {
    const next = (i + 1) % T;
    let da = angles[next] - angles[i];
    if (da < 0) da += 2 * Math.PI;
    const midAngle = angles[i] + da / 2;
    const labelR = R + nodeR + 22;
    const lx = (cx + labelR * Math.cos(midAngle)).toFixed(1);
    const ly = (cy + labelR * Math.sin(midAngle)).toFixed(1);
    const game = loop.trades[i][1];
    const label = game.length > 32 ? game.substring(0, 30) + '…' : game;
    const cosA = Math.cos(midAngle);
    const anchor = cosA > 0.3 ? 'start' : cosA < -0.3 ? 'end' : 'middle';
    parts.push(`<text x="${lx}" y="${ly}" text-anchor="${anchor}" dominant-baseline="central" font-family="Cormorant Garamond, serif" font-size="11" font-style="italic" fill="var(--text)" opacity="0.75">${esc(label)}</text>`);
  }

  for (let i = 0; i < T; i++) {
    const col = nodeColor(i);
    const p = pts[i];
    parts.push(`<circle cx="${p.x.toFixed(1)}" cy="${p.y.toFixed(1)}" r="${nodeR}" fill="${col}" opacity="0.9" stroke="var(--bg)" stroke-width="2"/>`);
    const uLabelR = R - nodeR - 18;
    const ux = (cx + uLabelR * Math.cos(angles[i])).toFixed(1);
    const uy = (cy + uLabelR * Math.sin(angles[i])).toFixed(1);
    const cosA = Math.cos(angles[i]);
    const uAnchor = cosA > 0.2 ? 'start' : cosA < -0.2 ? 'end' : 'middle';
    parts.push(`<text x="${ux}" y="${uy}" text-anchor="${uAnchor}" dominant-baseline="central" font-family="JetBrains Mono, monospace" font-size="9" font-weight="400" fill="${col}" opacity="0.9">${esc(loop.trades[i][0])}</text>`);
  }

  parts.push('</svg>');
  return parts.join('\\n');
}

// ── TEXT LIST ─────────────────────────────────────────────────────────────────

function makeTextList(loop) {
  const rows = loop.trades.map((t, i) =>
    `<div class="trade-row">` +
    `<span class="trade-idx">${String(i + 1).padStart(2, '0')}</span>` +
    `<span class="trade-giver">${esc(t[0])}</span>` +
    `<span class="trade-game">${esc(t[1])}</span>` +
    `<span class="trade-receiver">&rarr; ${esc(t[2])}</span>` +
    `</div>`
  ).join('');
  return `<div class="trade-list">${rows}</div>`;
}

// ── BUILD COVER ───────────────────────────────────────────────────────────────

function buildCover() {
  const grid = document.getElementById('coverGrid');
  LOOPS.forEach(loop => {
    const cell = document.createElement('div');
    cell.className = 'cover-cell';
    cell.innerHTML = makeCoverCircle(loop) +
      `<span class="cover-cell-label">Loop ${loop.n} &middot; ${loop.trades.length}</span>`;
    cell.addEventListener('click', () => {
      document.getElementById('loop' + loop.n).scrollIntoView({ behavior: 'smooth' });
    });
    grid.appendChild(cell);
  });
}

// ── BUILD LOOP SECTIONS ───────────────────────────────────────────────────────

function buildLoops() {
  const wrapper = document.getElementById('loopsWrapper');
  LOOPS.forEach((loop, idx) => {
    const section = document.createElement('div');
    section.className = 'loop-section';
    section.id = 'loop' + loop.n;
    const circle = isCircle(loop);
    const badge = circle ? 'Circle Diagram' : 'Trade List';
    section.innerHTML =
      `<div class="loop-header">` +
      `<div class="loop-num">${String(loop.n).padStart(2, '0')}</div>` +
      `<div><div class="loop-name">Loop ${loop.n}</div>` +
      `<div class="loop-meta">${loop.trades.length} trades</div></div>` +
      `<div class="loop-badge">${badge}</div></div>` +
      (circle
        ? `<div class="diagram-wrap">${makeCircleDiagram(loop)}</div>`
        : makeTextList(loop));
    wrapper.appendChild(section);
    if (idx < LOOPS.length - 1) {
      const div = document.createElement('div');
      div.className = 'divider';
      wrapper.appendChild(div);
    }
  });
}

buildCover();
buildLoops();
</script>
</body>
</html>"""

if __name__ == "__main__":
    main()
