# math-trade-genie

Math trade tools including visualizations, error-checking and more.

A four-block pipeline that turns a raw OLWLG results file into validated trade counts, human-readable trade loops, an HTML visualization, and a value-anomaly report.

## Pipeline

```
Raw OLWLG files (results.txt, wantsfile.txt)
        │
        ▼
Block 0 — Trade Counter          validated per-participant trade counts
        │
        ▼
Block 1 — Loop Parser            raw results → human-readable *_loops.txt
        │
        ├──▶ Block 2 — HTML Visualizer     *_loops.txt → self-contained HTML page
        │
        └──▶ Block 3 — Anomaly Detector    *_loops.txt → value-gap report
```

Block 1's `*_loops.txt` output is the hand-off contract that Blocks 2 and 3 both key off of.

## Quick Start

Run the whole pipeline (or any single block) through the interactive harness:

```
python run_genie.py
```

It prompts for a work folder, then lets you run Block 0, 1, 2, or 3 individually, or the full 0 → 1 → 2 → 3 chain in sequence.

## Blocks

| Block | Script | Input | Output | Purpose |
|---|---|---|---|---|
| 0 — Trade Counter | `00-trade-counter/mt_trade_counter.py` | Results file (OLWLG output) | `<results_stem>_trade_counts.txt` | Counts trades per participant, validates against header totals, produces a publishable list |
| 1 — Loop Parser | `01-loop-parser/mt_results_genie.py` | Results file + Wants file | `<results_stem>_loops.txt` | Translates raw OLWLG results into human-readable trade loops |
| 2 — HTML Visualizer | `02-html-visualizer/mt_loops_to_html.py` | `*_loops.txt` (Block 1 output) | `<loops_stem>_visualization.html` | Renders a polished, self-contained HTML visualization of the trade loops |
| 3 — Anomaly Detector | `03-anomaly-detector/mt_anomaly_detector.py` | `*_loops.txt` (Block 1 output) | Top-N (or all-pairs) value-gap report | Flags trades where the giver's item significantly exceeds the real-world value of what they receive |

Each block can also be run standalone — see the usage line in its own docstring for exact arguments.

## Requirements

- Python 3
- `ANTHROPIC_API_KEY` environment variable, for Block 3's Claude-based game valuations (falls back to a local `value_cache.json` once a game has been valued once; stated cash amounts in the wants file resolve without any API call at all)

## Repo Layout

```
00-trade-counter/       Block 0 script
01-loop-parser/         Block 1 script
02-html-visualizer/     Block 2 script
03-anomaly-detector/    Block 3 script
run_genie.py            Interactive harness — chains the blocks together
index.html              Hosted landing page for published visualizations
samples/                Example input/output files for each block
richmonds-most-unwanted/  Sibling tool (not part of the 0-3 pipeline) — see below
```

## Sibling Tools

**[Richmond's Most Unwanted — Rap Sheet Builder](richmonds-most-unwanted/README.md)**
takes Most Wanted/Unwanted GeekList exports (not OLWLG results files) and
builds a cross-trade Rap Sheet tracking which titles were Wanted/Unwanted in
each trade. It shares no data contract with Blocks 0-3 and isn't chained
into `run_genie.py` — run it standalone, once per trade, after the final run.
