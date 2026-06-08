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
echo "[0/5] Checking Python environment..."
python3 -c "import numpy, pandas, sklearn, matplotlib, statsmodels, openpyxl" \
    || { echo "ERROR: missing packages. Run: pip install -r code/requirements.txt"; exit 1; }

# --- 1. Verify data checksums
echo "[1/5] Verifying data files..."
python3 "$CODE/00_verify_data.py"

# --- 2. Spatial clustering (Experiment 1)
echo "[2/5] Running spatial clustering (Experiment 1)..."
cd "$CODE"
python3 02_clustering.py

# --- 3. Carbon analysis + DCGSI (Experiments 2 & 5)
echo "[3/5] Computing carbon intensity and DCGSI (Experiments 2 & 5)..."
python3 03_carbon_dcgsi.py

# --- 4. Demand growth regression (Experiment 3)
echo "[4/5] Running OLS regression with spatial diagnostics (Experiment 3)..."
python3 04_regression.py

# --- 5. Renewable Alignment Score (Experiment 4)
echo "[5/5] Computing Renewable Alignment Scores (Experiment 4)..."
python3 05_ras.py

cd "$ROOT"
echo ""
echo "======================================================="
echo "Reproduction complete. Outputs in results/:"
ls "$RESULTS/figures/"
echo "======================================================="
