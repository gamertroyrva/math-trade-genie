# Richmond's Most Unwanted — Rap Sheet Builder

A sibling tool, not part of the numbered 0→1→2→3 pipeline. It shares no data
contract with Blocks 0-3: its input is a **Most Wanted/Unwanted GeekList
export** (a pre-completion demand snapshot posted after a trade's want lists
close), not an OLWLG results/wants file, and it doesn't produce or consume
`*_loops.txt`.

Run it **once per math trade, after the final run** — not after every
practice run the way Blocks 0-3 typically get used.

## What it does

Takes every `most_wanted_*.txt` file in a folder (one per RVA No-Ship math
trade) and produces, in one pass:

1. **Per-trade QA metrics**, printed to the console — GeekList item counts,
   unique title counts, Wanted/Unwanted counts, Rule 1 overrides (titles
   that appeared in both sections), and any parsing anomalies.
2. **The Rap Sheet** (`rap_sheet.xlsx`, written to the same input folder) —
   one row per title, one column per trade, showing WANTED / UNWANTED /
   NOT_LISTED. Only titles that were UNWANTED at least once in some trade
   are included (titles that were always Wanted, every time, aren't part of
   this story).

Always a full rebuild from the complete set of raw files — there's no
incremental-append mode. Add a new trade's file to the folder and rerun.

## Usage

Requires `openpyxl` (`pip install openpyxl`).

```
python rap_sheet_builder.py [folder]
```

If `folder` is omitted, you'll be prompted for it. Trade IDs are inferred
from filenames (`most_wanted_2023_03.txt` → `2023_03`) and trades are
ordered chronologically by sorting those IDs as strings.

## Out of scope

Tiering ("true Most Unwanted" vs. second/third tier, streak scoring, owner
tracking) is a follow-up analysis phase that happens after a human reviews
the Rap Sheet — it isn't built here.
