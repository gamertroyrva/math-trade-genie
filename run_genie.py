#!/usr/bin/env python3
"""
Math Trade Genie — Run Harness
Drives Block 1, Block 2, and/or Block 3 against a single run folder.

Usage:
  python run_genie.py
"""

from pathlib import Path
import subprocess
import sys

# ── Resolve block script paths relative to this harness ───────────────────────

ROOT        = Path(__file__).parent
BLOCK1      = ROOT / "01-loop-parser"    / "mt_results_genie.py"
BLOCK2      = ROOT / "02-html-visualizer" / "mt_loops_to_html.py"
BLOCK3      = ROOT / "03-anomaly-detector" / "mt_anomaly_detector.py"


# ── Helpers ───────────────────────────────────────────────────────────────────

def prompt_work_folder() -> Path:
    while True:
        raw = input("\nWork folder path (full path to this run's folder):\n> ").strip()
        p = Path(raw)
        if p.exists() and p.is_dir():
            return p
        print(f"  Folder not found: {p}")
        print("  Please check the path and try again.")


def prompt_file_in_folder(folder: Path, prompt_text: str) -> Path:
    """Show all files in folder as a numbered menu; user picks by number."""
    while True:
        files = sorted([f.name for f in folder.iterdir() if f.is_file()])
        if not files:
            input(f"\n  (No files found in {folder.name}. Add files then press Enter to retry.)")
            continue
        print(f"\n  Files in {folder.name}:")
        for i, name in enumerate(files, 1):
            print(f"    {i}.  {name}")
        raw = input(f"\n{prompt_text} — enter a number:\n> ").strip()
        try:
            n = int(raw)
            if 1 <= n <= len(files):
                return folder / files[n - 1]
            print(f"  Please enter a number between 1 and {len(files)}.")
        except ValueError:
            print("  Please enter a number.")


def prompt_optional(prompt_text: str, default: str = "") -> str:
    raw = input(f"\n{prompt_text} (press Enter to skip):\n> ").strip()
    return raw if raw else default


def run_block(label: str, cmd: list) -> bool:
    """Run a subprocess command. Returns True on success."""
    print(f"\n{'─' * 60}")
    print(f"  Running {label}...")
    print(f"{'─' * 60}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\n  [!] {label} exited with errors (code {result.returncode})")
        return False
    print(f"\n  {label} complete.")
    return True


# ── Block runners ─────────────────────────────────────────────────────────────

def run_block1(work_folder: Path) -> bool:
    print("\n  Block 1 needs two input files from your work folder.")
    wants_file   = prompt_file_in_folder(work_folder, "Wants file")
    results_file = prompt_file_in_folder(work_folder, "Results file (OLWLG output)")
    cmd = [sys.executable, str(BLOCK1), str(results_file), str(wants_file)]
    return run_block("Block 1 — Loop Parser", cmd)


def run_block2(work_folder: Path) -> bool:
    loops_files = sorted(work_folder.glob("*_loops.txt"))

    if loops_files:
        loops_file = loops_files[0]
        print(f"\n  Found loops file: {loops_file.name}")
    else:
        loops_file = prompt_file_in_folder(work_folder, "Loops .txt file name:")

    title    = prompt_optional('Trade title for visualization  (e.g. "2026 East Coast Math Trade — PR 05")')
    subtitle = prompt_optional('Subtitle  (e.g. "BoardGameGeek · Eastern USA · Shipping")')

    cmd = [sys.executable, str(BLOCK2), str(loops_file)]
    if title:
        cmd += ["--title", title]
    if subtitle:
        cmd += ["--subtitle", subtitle]

    return run_block("Block 2 — HTML Visualizer", cmd)


def run_block3(work_folder: Path) -> bool:
    loops_files = sorted(work_folder.glob("*_loops.txt"))

    if loops_files:
        loops_file = loops_files[0]
        print(f"\n  Found loops file: {loops_file.name}")
    else:
        loops_file = prompt_file_in_folder(work_folder, "Loops .txt file name:")

    cmd = [sys.executable, str(BLOCK3), str(loops_file)]
    return run_block("Block 3 — Anomaly Detector", cmd)


# ── Menu ──────────────────────────────────────────────────────────────────────

MENU = """
╔══════════════════════════════════════╗
║      Math Trade Genie — Harness      ║
╠══════════════════════════════════════╣
║  1.  Block 1 — Loop Parser           ║
║  2.  Block 2 — HTML Visualizer       ║
║  3.  Block 3 — Anomaly Detector      ║
║  4.  Full Pipeline  (1 → 2 → 3)      ║
║  Q.  Quit                            ║
╚══════════════════════════════════════╝
"""

def main():
    print("\n" + "=" * 60)
    print("  Math Trade Genie — Run Harness")
    print("=" * 60)

    work_folder = prompt_work_folder()
    print(f"\n  Work folder set: {work_folder}")

    while True:
        print(MENU)
        choice = input("Choice: ").strip().upper()

        if choice == "1":
            run_block1(work_folder)
        elif choice == "2":
            run_block2(work_folder)
        elif choice == "3":
            run_block3(work_folder)
        elif choice == "4":
            print("\n  Running full pipeline: Block 1 → Block 2 → Block 3")
            ok = run_block1(work_folder)
            if ok:
                ok = run_block2(work_folder)
            if ok:
                run_block3(work_folder)
        elif choice == "Q":
            print("\n  Genie out. Good trading.\n")
            break
        else:
            print("  Not a valid choice. Try 1, 2, 3, 4, or Q.")


if __name__ == "__main__":
    main()