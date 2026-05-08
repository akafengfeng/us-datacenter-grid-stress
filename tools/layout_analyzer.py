#!/usr/bin/env python3
"""
PDF Layout Defect Detector

Compiles LaTeX, converts the resulting PDF to per-page PNGs, then analyzes
each page for common layout problems:
  - Excessive white space (> 35% of page area)
  - Oversized figures (> 50% of page height)
  - Orphan headings (heading in bottom 15% of page)
  - Widow lines (single line at top of page)
  - Blank pages

Outputs a markdown report to paper/layout_report.md.

Usage:
    python tools/layout_analyzer.py                     # uses ./paper/ as default
    python tools/layout_analyzer.py --paper-dir paper/
    python tools/layout_analyzer.py --pdf paper/main.pdf  # skip compilation
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# ---------------------------------------------------------------------------
# Optional dependencies
# ---------------------------------------------------------------------------

try:
    from PIL import Image
    import numpy as np
    HAS_IMAGING = True
except ImportError:
    HAS_IMAGING = False

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# LaTeX compilation
# ---------------------------------------------------------------------------

def compile_latex(paper_dir: Path) -> Path | None:
    """
    Compile main.tex via pdflatex + bibtex pipeline.

    Returns path to the compiled PDF, or None on failure.
    """
    tex_file = paper_dir / "main.tex"
    if not tex_file.exists():
        print(f"ERROR: {tex_file} not found.")
        return None

    print("Compiling LaTeX (pdflatex -> bibtex -> pdflatex -> pdflatex)...")

    commands = [
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
        ["bibtex", "main"],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
    ]

    for cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                cwd=str(paper_dir),
                capture_output=True,
                text=True,
                timeout=120,
            )
            # bibtex may warn but that is okay
            if cmd[0] == "pdflatex" and result.returncode != 0:
                print(f"  WARNING: {' '.join(cmd)} returned {result.returncode}")
                # Extract last error line
                for line in result.stdout.splitlines():
                    if line.startswith("!"):
                        print(f"    {line}")
        except FileNotFoundError:
            print(f"  ERROR: {cmd[0]} not found. Install texlive.")
            return None
        except subprocess.TimeoutExpired:
            print(f"  ERROR: {' '.join(cmd)} timed out.")
            return None

    pdf_path = paper_dir / "main.pdf"
    if pdf_path.exists():
        print(f"  Compiled: {pdf_path}")
        return pdf_path
    else:
        print("  ERROR: main.pdf not produced.")
        return None


# ---------------------------------------------------------------------------
# PDF to PNG conversion
# ---------------------------------------------------------------------------

def pdf_to_pngs(pdf_path: Path, output_dir: Path, dpi: int = 150) -> list[Path]:
    """
    Convert PDF to per-page PNGs using pdftoppm.

    Returns list of PNG paths sorted by page number.
    """
    if not shutil.which("pdftoppm"):
        print("ERROR: pdftoppm not found. Install poppler-utils:")
        print("  sudo apt-get install poppler-utils")
        return []

    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean old page images
    for old in output_dir.glob("page-*.png"):
        old.unlink()

    prefix = output_dir / "page"
    cmd = [
        "pdftoppm",
        "-png",
        "-r", str(dpi),
        str(pdf_path),
        str(prefix),
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=60, check=True)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: pdftoppm failed: {e}")
        return []
    except subprocess.TimeoutExpired:
        print("ERROR: pdftoppm timed out.")
        return []

    pngs = sorted(output_dir.glob("page-*.png"))
    print(f"  Converted {len(pngs)} pages to PNG.")
    return pngs


# ---------------------------------------------------------------------------
# Page analysis
# ---------------------------------------------------------------------------

def analyze_page(png_path: Path, page_num: int) -> dict:
    """
    Analyze a single page PNG for layout defects.

    Returns a dict with metrics and detected issues.
    """
    issues = []
    metrics = {"page": page_num, "path": str(png_path)}

    if not HAS_IMAGING:
        issues.append("SKIP: Pillow/numpy not installed — cannot analyze")
        metrics["issues"] = issues
        return metrics

    img = Image.open(png_path).convert("L")  # grayscale
    arr = np.array(img)
    h, w = arr.shape
    metrics["width"] = w
    metrics["height"] = h

    # --- White space ratio ---
    white_threshold = 245  # near-white pixels
    white_pixels = np.sum(arr > white_threshold)
    total_pixels = h * w
    white_ratio = white_pixels / total_pixels
    metrics["white_ratio"] = round(white_ratio, 3)

    if white_ratio > 0.60:
        issues.append(f"CRITICAL: {white_ratio:.0%} white space (likely blank or near-blank page)")
    elif white_ratio > 0.35:
        issues.append(f"WARNING: {white_ratio:.0%} white space (may indicate layout inefficiency)")

    # --- Oversized figure detection ---
    # Look for large dark-bordered rectangular regions (rough heuristic)
    # Check if any contiguous non-white vertical span exceeds 50% of page
    col_means = np.mean(arr, axis=1)  # average brightness per row
    content_rows = col_means < 240
    if np.any(content_rows):
        # Find longest contiguous run of content rows
        runs = []
        run_start = None
        for i, is_content in enumerate(content_rows):
            if is_content and run_start is None:
                run_start = i
            elif not is_content and run_start is not None:
                runs.append((run_start, i - run_start))
                run_start = None
        if run_start is not None:
            runs.append((run_start, h - run_start))

        if runs:
            longest_run = max(runs, key=lambda r: r[1])
            run_ratio = longest_run[1] / h
            metrics["largest_content_block_ratio"] = round(run_ratio, 3)
            if run_ratio > 0.50:
                issues.append(
                    f"INFO: Large content block ({run_ratio:.0%} of page height) — "
                    f"check if figure is too tall"
                )

    # --- Orphan heading detection ---
    # Heuristic: content in bottom 15% followed by white space in bottom 5%
    bottom_15 = arr[int(h * 0.85):int(h * 0.95), :]
    bottom_5 = arr[int(h * 0.95):, :]
    bottom_15_has_content = np.mean(bottom_15) < 235
    bottom_5_is_white = np.mean(bottom_5) > 245
    if bottom_15_has_content and bottom_5_is_white:
        issues.append("WARNING: Possible orphan heading (content near page bottom)")
    metrics["orphan_heading_risk"] = bottom_15_has_content and bottom_5_is_white

    # --- Widow line detection ---
    # Heuristic: thin content band at top (rows 0-5%) then white
    top_5 = arr[:int(h * 0.05), :]
    top_5_to_15 = arr[int(h * 0.05):int(h * 0.15), :]
    top_has_content = np.mean(top_5) < 240
    top_next_is_white = np.mean(top_5_to_15) > 245
    if top_has_content and top_next_is_white:
        issues.append("WARNING: Possible widow line (single line at page top)")
    metrics["widow_line_risk"] = top_has_content and top_next_is_white

    metrics["issues"] = issues
    return metrics


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(results: list[dict], output_path: Path):
    """Write the layout analysis report as markdown."""
    lines = [
        "# Layout Analysis Report",
        "",
        f"_Generated: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
        f"**Pages analyzed:** {len(results)}",
        "",
    ]

    total_issues = sum(len(r.get("issues", [])) for r in results)
    critical = sum(
        1 for r in results for i in r.get("issues", []) if i.startswith("CRITICAL")
    )
    warnings = sum(
        1 for r in results for i in r.get("issues", []) if i.startswith("WARNING")
    )

    lines.append(f"**Total issues:** {total_issues} "
                 f"({critical} critical, {warnings} warnings)")
    lines.append("")

    if total_issues == 0:
        lines.append("No layout issues detected. The paper looks clean.")
    else:
        lines.append("## Issues by Page")
        lines.append("")

        for r in results:
            issues = r.get("issues", [])
            if not issues:
                continue
            lines.append(f"### Page {r['page']}")
            lines.append(f"- White space: {r.get('white_ratio', 'N/A')}")
            for issue in issues:
                lines.append(f"- {issue}")
            lines.append("")

    lines.append("")
    lines.append("## Page Metrics")
    lines.append("")
    lines.append("| Page | White Space | Largest Block | Orphan Risk | Widow Risk |")
    lines.append("|------|-----------|---------------|-------------|------------|")
    for r in results:
        lines.append(
            f"| {r['page']} "
            f"| {r.get('white_ratio', 'N/A')} "
            f"| {r.get('largest_content_block_ratio', 'N/A')} "
            f"| {'Yes' if r.get('orphan_heading_risk') else 'No'} "
            f"| {'Yes' if r.get('widow_line_risk') else 'No'} |"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport written to: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="PDF Layout Defect Detector")
    parser.add_argument(
        "--paper-dir",
        default=str(ROOT / "paper"),
        help="Directory containing main.tex (default: paper/)",
    )
    parser.add_argument(
        "--pdf",
        default=None,
        help="Path to an already-compiled PDF (skip compilation)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="DPI for page rendering (default: 150)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output report path (default: paper/layout_report.md)",
    )
    args = parser.parse_args()

    paper_dir = Path(args.paper_dir).resolve()
    output_path = Path(args.output) if args.output else paper_dir / "layout_report.md"

    if not HAS_IMAGING:
        print("WARNING: Pillow and/or numpy not installed.")
        print("  pip install Pillow numpy")
        print("  Continuing with limited analysis...\n")

    # Step 1: Get or compile PDF
    if args.pdf:
        pdf_path = Path(args.pdf).resolve()
        if not pdf_path.exists():
            print(f"ERROR: PDF not found: {pdf_path}")
            sys.exit(1)
    else:
        pdf_path = compile_latex(paper_dir)
        if pdf_path is None:
            print("ERROR: LaTeX compilation failed. Cannot analyze layout.")
            sys.exit(1)

    # Step 2: Convert to PNGs
    page_dir = paper_dir / "page_images"
    pngs = pdf_to_pngs(pdf_path, page_dir, dpi=args.dpi)

    if not pngs:
        print("ERROR: No page images generated.")
        sys.exit(1)

    # Step 3: Analyze each page
    print("\nAnalyzing pages...")
    results = []
    for i, png in enumerate(pngs, start=1):
        result = analyze_page(png, page_num=i)
        results.append(result)
        issue_count = len(result.get("issues", []))
        status = f"  Page {i}: {issue_count} issue(s)" if issue_count else f"  Page {i}: OK"
        print(status)

    # Step 4: Generate report
    generate_report(results, output_path)


if __name__ == "__main__":
    main()
