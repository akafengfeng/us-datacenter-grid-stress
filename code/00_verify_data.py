"""
Data verification script.
Checks that all required data files are present and well-formed.
Run before any analysis scripts.

Exit codes:
  0 — all critical data present
  1 — critical data missing
"""
import os
import sys
import hashlib
import pandas as pd
from config import *


def check_file(path: str, description: str, critical: bool = True) -> bool:
    if os.path.exists(path):
        size_kb = os.path.getsize(path) / 1024
        print(f"  [OK]  {description} ({size_kb:.1f} KB)")
        return True
    else:
        level = "CRITICAL" if critical else "WARNING"
        print(f"  [{level}]  {description} — NOT FOUND: {path}")
        return not critical  # critical=True → return False (failure)


def verify_facility_csv() -> bool:
    """Check facility dataset integrity."""
    if not os.path.exists(FACILITY_FILE):
        print("  [CRITICAL]  Facility dataset not found.")
        return False
    df = pd.read_csv(FACILITY_FILE)
    required_cols = ["facility_id", "state", "lat", "lon", "it_load_mw_est",
                     "egrid_subrgn"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        print(f"  [CRITICAL]  Facility CSV missing columns: {missing}")
        return False
    n_valid = df.dropna(subset=["lat", "lon", "it_load_mw_est"]).shape[0]
    print(f"  [OK]  Facility dataset: {len(df)} rows, {n_valid} with valid coordinates")
    if n_valid < 50:
        print(f"  [WARNING]  Only {n_valid} valid facilities — expected ≥ 50")
    return True


def verify_egrid() -> bool:
    """Check eGRID data availability (Excel or CSV fallback)."""
    csv_path = os.path.join(DATA_DIR, "egrid2022", "egrid_subregion_rates.csv")
    if os.path.exists(EGRID_FILE):
        print(f"  [OK]  eGRID 2022 Excel ({os.path.getsize(EGRID_FILE)/1024:.0f} KB)")
        return True
    elif os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        print(f"  [OK]  eGRID 2022 CSV fallback ({len(df)} sub-regions)")
        required = ["SRVC", "ERCT", "RFCW", "AZNM", "SRCE",
                    "NWPP", "CAMX", "NYUP", "RFCE"]
        found = set(df.iloc[:, 0].tolist())
        missing = [r for r in required if r not in found]
        if missing:
            print(f"  [WARNING]  Missing sub-regions in CSV: {missing}")
        return True
    else:
        print(f"  [CRITICAL]  No eGRID data found.")
        print(f"    Download from: https://www.epa.gov/egrid/download-data")
        print(f"    Place at: {EGRID_FILE}")
        return False


def main():
    print("=" * 55)
    print("Data Verification")
    print("=" * 55)

    all_pass = True

    print("\n[Critical data files]")
    ok = verify_facility_csv()
    all_pass = all_pass and ok

    ok = verify_egrid()
    all_pass = all_pass and ok

    print("\n[Optional data files]")
    check_file(EIA_RETAIL_FILE,
               "EIA Table 5.6a (retail sales) — used for regression context",
               critical=False)
    check_file(EIA_GENERATION_FILE,
               "EIA Table 1.1 (generation) — used for state renewable fracs",
               critical=False)

    print("\n[Output directories]")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(FIGURES_DIR, exist_ok=True)
    print(f"  [OK]  {RESULTS_DIR}")
    print(f"  [OK]  {FIGURES_DIR}")

    print("\n" + "=" * 55)
    if all_pass:
        print("All critical data checks passed.")
        return 0
    else:
        print("FAILED: one or more critical data files are missing.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
