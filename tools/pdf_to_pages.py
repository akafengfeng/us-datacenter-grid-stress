#!/usr/bin/env python3
"""
PDF to Per-Page PNG Conversion

Converts a PDF file to individual PNG images (one per page) using pdftoppm
from the poppler-utils package. Creates thumbnails in paper/page_images/.

Usage:
    python tools/pdf_to_pages.py                           # default: paper/main.pdf
    python tools/pdf_to_pages.py --pdf paper/main.pdf
    python tools/pdf_to_pages.py --pdf paper/main.pdf --dpi 300 --output paper/page_images
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def check_pdftoppm() -> bool:
    """Check if pdftoppm is available."""
    if shutil.which("pdftoppm"):
        return True
    print("ERROR: pdftoppm not found.")
    print("Install poppler-utils:")
    print("  Ubuntu/Debian: sudo apt-get install poppler-utils")
    print("  macOS:         brew install poppler")
    print("  Fedora/RHEL:   sudo dnf install poppler-utils")
    return False


def get_page_count(pdf_path: Path) -> int | None:
    """Get the number of pages in a PDF using pdfinfo."""
    if not shutil.which("pdfinfo"):
        return None
    try:
        result = subprocess.run(
            ["pdfinfo", str(pdf_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        for line in result.stdout.splitlines():
            if line.startswith("Pages:"):
                return int(line.split(":")[1].strip())
    except (subprocess.TimeoutExpired, ValueError):
        pass
    return None


def pdf_to_pages(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 150,
    clean: bool = True,
) -> list[Path]:
    """
    Convert a PDF to per-page PNG files.

    Parameters
    ----------
    pdf_path : Path
        Path to the input PDF.
    output_dir : Path
        Directory to write page PNGs into.
    dpi : int
        Resolution for rendering (default 150 for thumbnails, 300 for print).
    clean : bool
        If True, remove old page images before generating new ones.

    Returns
    -------
    list[Path]
        Sorted list of generated PNG file paths.
    """
    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        return []

    if not check_pdftoppm():
        return []

    output_dir.mkdir(parents=True, exist_ok=True)

    # Clean old images if requested
    if clean:
        removed = 0
        for old_file in output_dir.glob("page-*.png"):
            old_file.unlink()
            removed += 1
        if removed:
            print(f"  Cleaned {removed} old page image(s).")

    # Get page count for progress reporting
    page_count = get_page_count(pdf_path)
    if page_count:
        print(f"  PDF has {page_count} page(s).")

    # Run pdftoppm
    prefix = output_dir / "page"
    cmd = [
        "pdftoppm",
        "-png",
        "-r", str(dpi),
        str(pdf_path),
        str(prefix),
    ]

    print(f"  Converting at {dpi} DPI...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"ERROR: pdftoppm failed (exit code {result.returncode})")
            if result.stderr:
                print(f"  {result.stderr.strip()}")
            return []
    except subprocess.TimeoutExpired:
        print("ERROR: pdftoppm timed out (120s limit).")
        return []

    # Collect results
    pngs = sorted(output_dir.glob("page-*.png"))
    print(f"  Generated {len(pngs)} page image(s) in {output_dir}/")

    # Print file sizes
    total_size = sum(p.stat().st_size for p in pngs)
    print(f"  Total size: {total_size / 1024:.0f} KB")

    return pngs


def main():
    parser = argparse.ArgumentParser(description="PDF to Per-Page PNG Conversion")
    parser.add_argument(
        "--pdf",
        default=str(ROOT / "paper" / "main.pdf"),
        help="Path to PDF file (default: paper/main.pdf)",
    )
    parser.add_argument(
        "--output",
        default=str(ROOT / "paper" / "page_images"),
        help="Output directory for page PNGs (default: paper/page_images/)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="DPI for rendering (default: 150; use 300 for high quality)",
    )
    parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not remove old page images before converting",
    )
    args = parser.parse_args()

    pdf_path = Path(args.pdf).resolve()
    output_dir = Path(args.output).resolve()

    if not pdf_path.exists():
        print(f"ERROR: PDF not found: {pdf_path}")
        print("  Compile your paper first: cd paper && pdflatex main.tex")
        sys.exit(1)

    pages = pdf_to_pages(
        pdf_path=pdf_path,
        output_dir=output_dir,
        dpi=args.dpi,
        clean=not args.no_clean,
    )

    if pages:
        print(f"\nDone. Page images saved to: {output_dir}/")
        for p in pages:
            print(f"  {p.name}")
    else:
        print("\nNo pages generated. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
