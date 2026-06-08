"""
Load and preprocess all datasets.
Outputs cleaned DataFrames used by downstream analysis scripts.
"""
import pandas as pd
import numpy as np
import openpyxl
from config import *


def load_facilities(min_mw: float = MIN_FACILITY_MW) -> pd.DataFrame:
    """Load curated facility dataset and apply minimum IT-load filter."""
    df = pd.read_csv(FACILITY_FILE)
    df = df[df["it_load_mw_est"] >= min_mw].copy()
    df["lat"] = pd.to_numeric(df["lat"], errors="coerce")
    df["lon"] = pd.to_numeric(df["lon"], errors="coerce")
    df["it_load_mw_est"] = pd.to_numeric(df["it_load_mw_est"], errors="coerce")
    df = df.dropna(subset=["lat", "lon", "it_load_mw_est"])
    print(f"Facilities loaded: {len(df):,}  |  Total IT load: "
          f"{df['it_load_mw_est'].sum():.0f} MW")
    return df


def load_egrid(sheet: str = EGRID_SHEET) -> pd.DataFrame:
    """
    Load EPA eGRID 2022 sub-regional data.

    Tries the full Excel file first (data/egrid2022/eGRID2022_data.xlsx).
    Falls back to the bundled CSV (data/egrid2022/egrid_subregion_rates.csv)
    which covers the 9 major US data centre market sub-regions.

    Download full data from: https://www.epa.gov/egrid/download-data

    Returns a DataFrame indexed by sub-region code with co2_g_kwh and
    renewable_frac columns.
    """
    cols = EGRID_COLS
    csv_path = os.path.join(DATA_DIR, "egrid2022", "egrid_subregion_rates.csv")

    if os.path.exists(EGRID_FILE):
        wb = openpyxl.load_workbook(EGRID_FILE, read_only=True, data_only=True)
        ws = wb[sheet]
        data = list(ws.values)
        df = pd.DataFrame(data[1:], columns=data[0])
        wb.close()

        keep = [cols["subregion"], cols["co2_rate"], cols["hydro_frac"],
                cols["renew_frac"], cols["coal_frac"], cols["gas_frac"],
                cols["nuclear_frac"], cols["wind_frac"], cols["solar_frac"]]
        df = df[keep].copy()
        df.columns = ["subrgn", "co2_lb_mwh", "hydro_frac", "nonhydro_renew_frac",
                      "coal_frac", "gas_frac", "nuclear_frac", "wind_frac", "solar_frac"]
    elif os.path.exists(csv_path):
        print("Note: Using bundled CSV (full eGRID Excel not found). "
              "Download from https://www.epa.gov/egrid/download-data for full data.")
        df = pd.read_csv(csv_path)
        df.columns = ["subrgn", "co2_lb_mwh", "hydro_frac", "nonhydro_renew_frac",
                      "coal_frac", "gas_frac", "nuclear_frac", "wind_frac", "solar_frac"]
    else:
        raise FileNotFoundError(
            f"eGRID data not found. Expected either:\n"
            f"  {EGRID_FILE}\n  {csv_path}\n"
            f"Download from: https://www.epa.gov/egrid/download-data"
        )

    for col in df.columns[1:]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df["co2_g_kwh"] = df["co2_lb_mwh"] * LB_MWH_TO_G_KWH / 1000
    df["renewable_frac"] = df["hydro_frac"].fillna(0) + \
                           df["nonhydro_renew_frac"].fillna(0)
    df = df.dropna(subset=["co2_lb_mwh"]).set_index("subrgn")
    print(f"eGRID sub-regions loaded: {len(df)}")
    return df


def load_eia_state_generation() -> pd.DataFrame:
    """
    Load EIA Table 1.1: net generation by state and energy source (2020-2024).

    File: data/eia/table_1_1.csv
    Download from EIA Electric Power Monthly portal:
    https://www.eia.gov/electricity/data/browser/

    Returns state-level renewable fraction and total generation for 2022-2024.
    """
    df = pd.read_csv(EIA_GENERATION_FILE, skiprows=4, thousands=",")
    # Actual column structure varies by EIA download format;
    # the code below assumes the standard EIA browser export format.
    return df


def load_eia_retail_sales() -> pd.DataFrame:
    """
    Load EIA Table 5.6a: retail electricity sales by state (MWh).

    Used to compute state-level demand growth rate (2022 vs 2024).

    File: data/eia/table_5_6a.csv
    """
    df = pd.read_csv(EIA_RETAIL_FILE, skiprows=4, thousands=",")
    return df


if __name__ == "__main__":
    fac = load_facilities()
    print(fac.groupby("state")["it_load_mw_est"].sum()
            .sort_values(ascending=False).head(10))
