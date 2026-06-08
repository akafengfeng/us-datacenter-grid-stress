"""
Configuration for data centre grid stress analysis.
All random seeds and file paths are set here for full reproducibility.
"""
import os

# ------------------------------------------------------------------
# Reproducibility
# ------------------------------------------------------------------
RANDOM_SEED = 42

# ------------------------------------------------------------------
# Paths
# ------------------------------------------------------------------
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
RESULTS_DIR = os.path.join(ROOT_DIR, "results")
FIGURES_DIR = os.path.join(RESULTS_DIR, "figures")

EGRID_FILE = os.path.join(DATA_DIR, "egrid2022", "eGRID2022_data.xlsx")
EGRID_SHEET = "SUBRGN22"

FACILITY_FILE = os.path.join(DATA_DIR, "facilities", "us_datacenters_2024q1.csv")

EIA_RETAIL_FILE = os.path.join(DATA_DIR, "eia", "table_5_6a.csv")
EIA_GENERATION_FILE = os.path.join(DATA_DIR, "eia", "table_1_1.csv")

# ------------------------------------------------------------------
# Analysis parameters
# ------------------------------------------------------------------
K_CLUSTERS = 8          # Number of spatial clusters
MIN_FACILITY_MW = 1     # Minimum IT load (MW) to include
N_BOOTSTRAP = 2000      # Bootstrap resamples for confidence intervals
CI_LEVEL = 0.95         # Confidence interval coverage

# DCGSI weights (baseline equal-weight specification)
DCGSI_WEIGHTS = {
    "demand_growth":      0.25,
    "colocation_density": 0.25,
    "grid_headroom":      0.25,   # enters as (1 - normalised value)
    "renewable_deficit":  0.25,   # enters as (1 - normalised renewable frac)
}

# Moran's I spatial weights matrix bandwidth (km)
MORANS_BANDWIDTH_KM = 500

# Social cost of carbon (USD/tonne CO2), per US IWG 2023
SOCIAL_COST_CARBON = 190.0   # USD / tonne CO2

# Representative data centre for carbon cost illustration
ILLUSTRATIVE_DC_MW = 200     # MW IT load
ILLUSTRATIVE_PUE   = 1.2     # Power usage effectiveness
ILLUSTRATIVE_UTIL  = 0.90    # Average utilisation

# ------------------------------------------------------------------
# eGRID column names (sheet SUBRGN22, eGRID 2022)
# ------------------------------------------------------------------
EGRID_COLS = {
    "subregion":    "SUBRGN",
    "co2_rate":     "SRCO2EQA",   # lb CO2eq / MWh
    "coal_frac":    "SRCLPR",
    "gas_frac":     "SRNGPR",
    "nuclear_frac": "SRNUCPR",
    "hydro_frac":   "SRHYDPR",
    "wind_frac":    "SRWNDPR",
    "solar_frac":   "SRSOLPR",
    "renew_frac":   "SRNGEPR",    # non-hydro renewables
}

# lb/MWh → g/kWh conversion factor
LB_MWH_TO_G_KWH = 453.592
