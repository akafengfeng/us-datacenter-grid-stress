#!/usr/bin/env bash
# ============================================================
# reproduce.sh — regenerates all key figures and tables
# Run from the repository root: bash results/reproduce.sh
# Requires: Python 3.11+, packages in code/requirements.txt
# ============================================================
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODE="$ROOT/code"
RESULTS="$ROOT/results"

echo "======================================================="
echo "AIDER Reproduction Script"
echo "Data Centre Grid Stress — Feng Wei, CAICT"
echo "======================================================="

# --- 0. Environment check
echo "[0/6] Checking Python environment..."
python3 -c "import numpy, pandas, sklearn, matplotlib, statsmodels, openpyxl" \
    || { echo "ERROR: missing packages. Run: pip install -r code/requirements.txt"; exit 1; }

# --- 1. Verify data checksums
echo "[1/6] Verifying data files..."
python3 "$CODE/00_verify_data.py"

# --- 2. Bibliometric figure (Figure 2)
echo "[2/6] Generating bibliometric analysis figure..."
python3 "$CODE/00_bibliometrics.py"

# --- 3. Spatial clustering (Experiment 1)
echo "[3/6] Running spatial clustering (Experiment 1)..."
cd "$CODE"
python3 02_clustering.py

# --- 4. Carbon analysis + DCGSI (Experiments 2 & 5)
echo "[4/6] Computing carbon intensity and DCGSI (Experiments 2 & 5)..."
python3 03_carbon_dcgsi.py

# --- 5. Demand growth regression (Experiment 3)
echo "[5/6] Running OLS regression with spatial diagnostics (Experiment 3)..."
python3 04_regression.py

# --- 6. Renewable Alignment Score + renewable alignment figure (Experiment 4)
echo "[6/6] Computing Renewable Alignment Scores (Experiment 4)..."
python3 05_ras.py

cd "$ROOT"

# Sync figures to results/figures/ for reproducibility record
mkdir -p "$RESULTS/figures"
cp "$ROOT/paper/figures/"*.pdf "$RESULTS/figures/" 2>/dev/null || true

echo ""
echo "======================================================="
echo "Reproduction complete. Outputs in results/:"
ls "$RESULTS/figures/"
echo "======================================================="
