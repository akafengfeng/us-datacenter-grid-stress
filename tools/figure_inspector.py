#!/usr/bin/env python3
"""
Figure Quality Analyzer

Two analysis modes:
  --script path   Analyze a Python figure-generation script
  --image  path   Analyze a rendered PNG/PDF image

Can also run in batch mode on all figures:
  --all           Analyze all scripts in code/figures/ and images in paper/figures/

Outputs per-figure scores (1-10) and a combined report to paper/figure_report.md.

Usage:
    python tools/figure_inspector.py --script code/figures/fig_results.py
    python tools/figure_inspector.py --image paper/figures/fig_results.png
    python tools/figure_inspector.py --all
"""

import argparse
import ast
import re
import sys
from datetime import datetime
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
# Script analysis
# ---------------------------------------------------------------------------

# Patterns that suggest lazy or low-effort figure generation
AI_LAZY_PATTERNS = [
    (r"plt\.plot\(.{0,20}\)", "bare plt.plot without customization"),
    (r"plt\.show\(\)", "plt.show() — figures should be saved, not shown interactively"),
    (r"plt\.title\(", "plt.title() — use ax.set_title() for better control"),
    (r"plt\.xlabel\(", "plt.xlabel() — use ax.set_xlabel() for better control"),
    (r"plt\.ylabel\(", "plt.ylabel() — use ax.set_ylabel() for better control"),
    (r"color=['\"](?:red|blue|green|yellow|cyan|magenta)['\"]",
     "basic color name — use hex/named palette from plotting_utils"),
    (r"figsize=\(\s*1[0-9]", "very large figsize — journal columns are 3.5-7 inches"),
    (r"fontsize=\s*(?:1[5-9]|[2-9]\d)", "large font size — journal standard is 8-12pt"),
    (r"\.legend\(.*loc=['\"]best['\"]",
     "legend loc='best' — explicitly place legends for reproducibility"),
    (r"np\.random\.", "random data generation — figures must use real computed data"),
]

# Desirable matplotlib functions/patterns
GOOD_PATTERNS = [
    (r"from\s+.*plotting_utils\s+import", "uses plotting_utils"),
    (r"setup_style\(\)", "calls setup_style()"),
    (r"save_figure\(", "uses save_figure()"),
    (r"ax\.\w+", "uses axes-level API (good)"),
    (r"fig,\s*ax", "creates figure with axes"),
    (r"\.set_xlabel\(", "sets axis labels"),
    (r"\.set_ylabel\(", "sets axis labels"),
    (r"\.annotate\(", "adds annotations"),
    (r"\.axhline\(|\.axvline\(", "adds reference lines"),
    (r"\.fill_between\(", "uses uncertainty bands"),
    (r"\.errorbar\(", "plots error bars"),
    (r"colorbar", "includes colorbar"),
    (r"GridSpec|subplot_mosaic|subplots\(.*,", "uses multi-panel layout"),
    (r"tight_layout|constrained_layout", "manages layout"),
    (r"bbox_inches=['\"]tight['\"]", "tight bounding box on save"),
]


def analyze_script(script_path: Path) -> dict:
    """
    Analyze a Python figure-generation script for quality indicators.

    Returns a dict with metrics, issues, positives, and a score (1-10).
    """
    result = {
        "path": str(script_path),
        "type": "script",
        "issues": [],
        "positives": [],
        "metrics": {},
    }

    if not script_path.exists():
        result["issues"].append(f"File not found: {script_path}")
        result["score"] = 0
        return result

    content = script_path.read_text(encoding="utf-8", errors="replace")
    lines = content.splitlines()
    result["metrics"]["line_count"] = len(lines)

    # --- Parse AST for structural analysis ---
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        result["issues"].append(f"SyntaxError: {e}")
        result["score"] = 1
        return result

    # Count function definitions
    func_count = sum(1 for node in ast.walk(tree) if isinstance(node, ast.FunctionDef))
    result["metrics"]["function_count"] = func_count
    if func_count == 0:
        result["issues"].append("No functions defined — script-style code is harder to maintain")

    # Count imports
    import_count = sum(
        1 for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    )
    result["metrics"]["import_count"] = import_count

    # --- Check for plotting_utils import ---
    has_plotting_utils = bool(re.search(r"plotting_utils", content))
    if has_plotting_utils:
        result["positives"].append("Imports from plotting_utils (consistent styling)")
    else:
        result["issues"].append("Does not import plotting_utils — figure style may be inconsistent")

    # --- Count subplots ---
    subplot_matches = re.findall(r"subplots?\(", content)
    subplot_count = len(subplot_matches)
    result["metrics"]["subplot_calls"] = subplot_count

    # --- Check for annotations ---
    annotation_matches = re.findall(r"\.annotate\(|\.text\(|\.set_title\(", content)
    result["metrics"]["annotation_count"] = len(annotation_matches)
    if len(annotation_matches) == 0:
        result["issues"].append("No annotations or titles — figures should be self-explanatory")

    # --- AI-lazy pattern detection ---
    lazy_count = 0
    for pattern, description in AI_LAZY_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            lazy_count += len(matches)
            result["issues"].append(f"Lazy pattern: {description} ({len(matches)}x)")

    result["metrics"]["lazy_pattern_count"] = lazy_count

    # --- Good pattern detection ---
    good_count = 0
    for pattern, description in GOOD_PATTERNS:
        if re.search(pattern, content):
            good_count += 1
            result["positives"].append(description)

    result["metrics"]["good_pattern_count"] = good_count

    # --- Docstring check ---
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
        result["positives"].append("Has module docstring")
    else:
        result["issues"].append("Missing module docstring")

    # --- Score calculation ---
    score = 5  # baseline

    # Positives
    if has_plotting_utils:
        score += 1
    if good_count >= 5:
        score += 1
    if good_count >= 8:
        score += 1
    if func_count >= 1:
        score += 0.5
    if len(annotation_matches) >= 2:
        score += 0.5

    # Negatives
    if lazy_count >= 3:
        score -= 2
    elif lazy_count >= 1:
        score -= 1
    if not has_plotting_utils:
        score -= 1
    if len(annotation_matches) == 0:
        score -= 0.5
    if len(lines) < 20:
        score -= 1  # suspiciously short

    score = max(1, min(10, round(score)))
    result["score"] = score
    return result


# ---------------------------------------------------------------------------
# Image analysis
# ---------------------------------------------------------------------------

def analyze_image(image_path: Path) -> dict:
    """
    Analyze a rendered figure image for quality indicators.

    Returns a dict with metrics, issues, positives, and a score (1-10).
    """
    result = {
        "path": str(image_path),
        "type": "image",
        "issues": [],
        "positives": [],
        "metrics": {},
    }

    if not image_path.exists():
        result["issues"].append(f"File not found: {image_path}")
        result["score"] = 0
        return result

    if not HAS_IMAGING:
        result["issues"].append(
            "Pillow/numpy not installed — cannot analyze image. "
            "Install: pip install Pillow numpy"
        )
        result["score"] = 5  # neutral
        return result

    try:
        img = Image.open(image_path)
    except Exception as e:
        result["issues"].append(f"Cannot open image: {e}")
        result["score"] = 1
        return result

    w, h = img.size
    result["metrics"]["width_px"] = w
    result["metrics"]["height_px"] = h
    result["metrics"]["aspect_ratio"] = round(w / h, 2) if h > 0 else 0

    # --- DPI check ---
    dpi = img.info.get("dpi", (72, 72))
    if isinstance(dpi, tuple):
        dpi_val = dpi[0]
    else:
        dpi_val = dpi
    result["metrics"]["dpi"] = dpi_val

    if dpi_val < 150:
        result["issues"].append(f"Low DPI ({dpi_val}) — journals require >= 300 DPI")
    elif dpi_val >= 300:
        result["positives"].append(f"Good DPI ({dpi_val})")

    # --- Aspect ratio check ---
    ar = w / h if h > 0 else 1
    if ar > 2.5:
        result["issues"].append(f"Very wide aspect ratio ({ar:.1f}) — may not fit column")
    elif ar < 0.4:
        result["issues"].append(f"Very tall aspect ratio ({ar:.1f}) — may dominate page")
    else:
        result["positives"].append(f"Reasonable aspect ratio ({ar:.2f})")

    # Convert to numpy for pixel analysis
    arr = np.array(img.convert("RGB"))

    # --- White space analysis ---
    gray = np.mean(arr, axis=2)
    white_ratio = np.mean(gray > 245)
    result["metrics"]["white_ratio"] = round(float(white_ratio), 3)

    if white_ratio > 0.50:
        result["issues"].append(
            f"Excessive white space ({white_ratio:.0%}) — "
            f"figure has poor data-ink ratio"
        )
    elif white_ratio > 0.35:
        result["issues"].append(f"Moderate white space ({white_ratio:.0%})")
    else:
        result["positives"].append(f"Good data-ink ratio (white space: {white_ratio:.0%})")

    # --- Color diversity ---
    # Sample pixels and count unique hues
    flat = arr.reshape(-1, 3)
    # Subsample for speed
    if len(flat) > 50000:
        indices = np.random.default_rng(42).choice(len(flat), 50000, replace=False)
        flat = flat[indices]

    # Convert to simple color bins (divide each channel by 32 -> 8 bins)
    binned = (flat // 32).astype(np.uint8)
    unique_colors = len(np.unique(binned, axis=0))
    result["metrics"]["color_diversity"] = unique_colors

    if unique_colors < 10:
        result["issues"].append(
            f"Very low color diversity ({unique_colors} bins) — "
            f"may be too simple or monotone"
        )
    elif unique_colors > 200:
        result["positives"].append(f"Rich color palette ({unique_colors} color bins)")

    # --- Edge complexity (proxy for detail level) ---
    try:
        from PIL import ImageFilter
        edges = img.convert("L").filter(ImageFilter.FIND_EDGES)
        edge_arr = np.array(edges)
        edge_density = np.mean(edge_arr > 30)
        result["metrics"]["edge_density"] = round(float(edge_density), 4)

        if edge_density < 0.01:
            result["issues"].append("Very low edge density — figure may lack detail")
        elif edge_density > 0.15:
            result["issues"].append("High edge density — figure may be too cluttered")
        else:
            result["positives"].append(f"Good edge density ({edge_density:.3f})")
    except Exception:
        pass

    # --- Panel detection (rough: look for internal white gutters) ---
    # Horizontal gutters: rows that are nearly all white
    row_means = np.mean(gray, axis=1)
    gutter_rows = row_means > 248
    # Count transitions from content to gutter
    transitions = np.sum(np.diff(gutter_rows.astype(int)) == 1)
    panel_estimate = max(1, transitions)
    result["metrics"]["estimated_panels"] = panel_estimate

    if panel_estimate > 1:
        result["positives"].append(f"Multi-panel figure (~{panel_estimate} panels)")

    # --- Score calculation ---
    score = 5  # baseline

    # Positives
    if dpi_val >= 300:
        score += 1
    if white_ratio < 0.35:
        score += 1
    if 0.5 < ar < 2.0:
        score += 0.5
    if unique_colors > 50:
        score += 0.5
    if panel_estimate > 1:
        score += 0.5
    if unique_colors > 100:
        score += 0.5

    # Negatives
    if dpi_val < 150:
        score -= 2
    if white_ratio > 0.50:
        score -= 2
    elif white_ratio > 0.35:
        score -= 1
    if unique_colors < 10:
        score -= 1
    if ar > 2.5 or ar < 0.4:
        score -= 1

    score = max(1, min(10, round(score)))
    result["score"] = score
    return result


# ---------------------------------------------------------------------------
# Batch analysis
# ---------------------------------------------------------------------------

def find_all_scripts(code_figures_dir: Path) -> list[Path]:
    """Find all Python figure scripts."""
    if not code_figures_dir.exists():
        return []
    return sorted(code_figures_dir.glob("*.py"))


def find_all_images(paper_figures_dir: Path) -> list[Path]:
    """Find all rendered figure images."""
    if not paper_figures_dir.exists():
        return []
    extensions = ("*.png", "*.jpg", "*.jpeg", "*.pdf")
    images = []
    for ext in extensions:
        images.extend(paper_figures_dir.glob(ext))
    return sorted(images)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_report(results: list[dict], output_path: Path):
    """Write figure analysis report as markdown."""
    lines = [
        "# Figure Quality Report",
        "",
        f"_Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}_",
        "",
        f"**Figures analyzed:** {len(results)}",
        "",
    ]

    if not results:
        lines.append("No figures found to analyze.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    # Summary table
    avg_score = sum(r["score"] for r in results) / len(results) if results else 0
    lines.append(f"**Average score:** {avg_score:.1f}/10")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Figure | Type | Score | Key Issue |")
    lines.append("|--------|------|-------|-----------|")

    for r in results:
        name = Path(r["path"]).name
        fig_type = r["type"]
        score = r["score"]
        key_issue = r["issues"][0] if r["issues"] else "None"
        # Truncate long issues
        if len(key_issue) > 60:
            key_issue = key_issue[:57] + "..."
        lines.append(f"| {name} | {fig_type} | {score}/10 | {key_issue} |")

    lines.append("")

    # Detailed per-figure analysis
    lines.append("## Detailed Analysis")
    lines.append("")

    for r in results:
        name = Path(r["path"]).name
        lines.append(f"### {name}")
        lines.append(f"- **Type:** {r['type']}")
        lines.append(f"- **Score:** {r['score']}/10")
        lines.append(f"- **Path:** `{r['path']}`")
        lines.append("")

        if r.get("metrics"):
            lines.append("**Metrics:**")
            for k, v in r["metrics"].items():
                lines.append(f"- {k}: {v}")
            lines.append("")

        if r.get("positives"):
            lines.append("**Strengths:**")
            for p in r["positives"]:
                lines.append(f"- {p}")
            lines.append("")

        if r.get("issues"):
            lines.append("**Issues:**")
            for issue in r["issues"]:
                lines.append(f"- {issue}")
            lines.append("")

        lines.append("---")
        lines.append("")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport written to: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Figure Quality Analyzer")
    parser.add_argument("--script", help="Path to a Python figure script to analyze")
    parser.add_argument("--image", help="Path to a rendered figure image to analyze")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze all scripts in code/figures/ and images in paper/figures/",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output report path (default: paper/figure_report.md)",
    )
    args = parser.parse_args()

    output_path = Path(args.output) if args.output else ROOT / "paper" / "figure_report.md"

    if not args.script and not args.image and not args.all:
        print("ERROR: Specify --script, --image, or --all")
        parser.print_help()
        sys.exit(1)

    results = []

    if args.script:
        path = Path(args.script).resolve()
        print(f"Analyzing script: {path}")
        r = analyze_script(path)
        results.append(r)
        print(f"  Score: {r['score']}/10")
        for issue in r["issues"]:
            print(f"  Issue: {issue}")
        for pos in r["positives"]:
            print(f"  Good:  {pos}")

    if args.image:
        path = Path(args.image).resolve()
        print(f"Analyzing image: {path}")
        r = analyze_image(path)
        results.append(r)
        print(f"  Score: {r['score']}/10")
        for issue in r["issues"]:
            print(f"  Issue: {issue}")
        for pos in r["positives"]:
            print(f"  Good:  {pos}")

    if args.all:
        print("Batch analysis mode\n")

        # Scripts
        scripts = find_all_scripts(ROOT / "code" / "figures")
        if scripts:
            print(f"Found {len(scripts)} figure script(s):")
            for s in scripts:
                print(f"  Analyzing: {s.name}")
                r = analyze_script(s)
                results.append(r)
                print(f"    Score: {r['score']}/10 "
                      f"({len(r['issues'])} issues, {len(r['positives'])} positives)")
        else:
            print("No figure scripts found in code/figures/")

        print()

        # Images
        images = find_all_images(ROOT / "paper" / "figures")
        if images:
            print(f"Found {len(images)} figure image(s):")
            for img_path in images:
                print(f"  Analyzing: {img_path.name}")
                r = analyze_image(img_path)
                results.append(r)
                print(f"    Score: {r['score']}/10 "
                      f"({len(r['issues'])} issues, {len(r['positives'])} positives)")
        else:
            print("No figure images found in paper/figures/")

    if results:
        generate_report(results, output_path)

        # Print summary
        avg = sum(r["score"] for r in results) / len(results)
        print(f"\nOverall average score: {avg:.1f}/10")
        if avg < 5:
            print("VERDICT: Figures need significant improvement.")
        elif avg < 7:
            print("VERDICT: Figures are acceptable but could be better.")
        else:
            print("VERDICT: Figures meet publication quality standards.")
    else:
        print("No figures analyzed.")


if __name__ == "__main__":
    main()
