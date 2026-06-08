"""
Experiments 2 & 5: Carbon intensity analysis and DCGSI computation.

Reads:
  results/cluster_stats.csv       (from 02_clustering.py)
  data/egrid2022/eGRID2022_data.xlsx
  data/eia/table_5_6a.csv         (demand growth)

Outputs:
  results/carbon_analysis.csv
  results/dcgsi_scores.csv
  results/figures/fig_carbon.pdf
  results/figures/fig_dcgsi.pdf
  results/figures/fig_renewable_alignment.pdf
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import spearmanr
from config import *
from load_data import load_egrid

os.makedirs(FIGURES_DIR, exist_ok=True)

# ------------------------------------------------------------------
# Market definitions: eGRID sub-region and input parameters
# sourced from EPA eGRID 2022, NERC 2024 LTRA, utility IRP filings
# ------------------------------------------------------------------
MARKETS = pd.DataFrame([
    # label, egrid_subrgn, capacity_share_pct, dc_demand_growth_pct_yr,
    # transmission_headroom_frac, renewable_frac_2023
    # Sources: eGRID 2022 (col SRCO2EQA); Dominion IRP 2024; ERCOT 2024 LTLF;
    #          EIA EPM 2024; NERC 2024 LTRA; FERC eLibrary
    ("Northern Virginia", "SRVC",  31.2,  12.4, 0.058, 0.148),
    ("Dallas–Fort Worth", "ERCT",  15.5,   8.7, 0.121, 0.348),
    ("Chicago Metro",     "RFCW",   8.5,   4.2, 0.098, 0.197),
    ("Phoenix",           "AZNM",   7.9,   5.8, 0.132, 0.124),
    ("Atlanta",           "SRCE",   7.0,   6.3, 0.089, 0.132),
    ("Pacific Northwest", "NWPP",   5.5,   2.1, 0.291, 0.721),
    ("SF Bay Area",       "CAMX",   5.4,   2.8, 0.148, 0.583),
    ("NYC Metro",         "NYUP",   5.0,   3.1, 0.074, 0.263),
    ("Dispersed",         "RFCE",  14.0,   2.5, 0.180, 0.220),
], columns=["market", "egrid_subrgn", "cap_share_pct",
            "dc_growth_pct", "tx_headroom", "renew_frac"])


def merge_egrid(markets: pd.DataFrame, egrid: pd.DataFrame) -> pd.DataFrame:
    """Join eGRID emission rates onto market table."""
    egrid_slim = egrid[["co2_g_kwh"]].reset_index()
    egrid_slim = egrid_slim.rename(columns={egrid_slim.columns[0]: "egrid_subrgn"})
    df = markets.merge(egrid_slim, on="egrid_subrgn", how="left")
    # For sub-regions not found in eGRID (e.g. dispersed), impute national avg
    nat_avg = egrid["co2_g_kwh"].mean()
    df["co2_g_kwh"] = df["co2_g_kwh"].fillna(nat_avg)
    return df


def carbon_analysis(df: pd.DataFrame) -> dict:
    """Compute fleet-average carbon intensity and counterfactual."""
    total_share = df["cap_share_pct"].sum()
    # Weighted average: current fleet
    df["weighted_co2"] = df["co2_g_kwh"] * df["cap_share_pct"] / total_share
    fleet_avg = df["weighted_co2"].sum()

    # Counterfactual: redistribute capacity proportional to renewable fraction
    df["renewable_weight"] = df["renew_frac"] * df["cap_share_pct"]
    cf_share = df["renewable_weight"] / df["renewable_weight"].sum() * total_share
    cf_avg = (df["co2_g_kwh"] * cf_share / total_share).sum()

    return {
        "fleet_avg_g_kwh":          fleet_avg,
        "counterfactual_g_kwh":     cf_avg,
        "reduction_pct":            (fleet_avg - cf_avg) / fleet_avg * 100,
        "nat_avg_g_kwh":            df["co2_g_kwh"].mean(),
    }


def compute_dcgsi(df: pd.DataFrame,
                  weights: dict = DCGSI_WEIGHTS) -> pd.DataFrame:
    """
    Compute Data Centre Grid Stress Index (DCGSI) for each market.

    Components (all normalised to [0,1] via min-max over market rows):
      G  = annual DC demand growth rate          (higher → more stress)
      C  = colocation density ≈ cap_share_pct    (higher → more stress)
      H  = transmission headroom fraction        (higher → LESS stress; enter as 1−H̃)
      R  = local renewable fraction 2023         (higher → LESS stress; enter as 1−R̃)

    Weight justification (see Section 8.2):
      Equal weights (0.25 each) are used as the baseline specification,
      consistent with the composite index literature when no empirical
      calibration dataset is available (OECD 2008). Sensitivity analysis
      over the full weight simplex is reported in results/dcgsi_sensitivity.csv.
    """
    df = df.copy()

    def minmax(s):
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng > 0 else pd.Series(0.0, index=s.index)

    df["G_norm"] = minmax(df["dc_growth_pct"])
    df["C_norm"] = minmax(df["cap_share_pct"])
    df["H_norm"] = minmax(df["tx_headroom"])
    df["R_norm"] = minmax(df["renew_frac"])

    w = weights
    df["dcgsi"] = (
        w["demand_growth"]      * df["G_norm"] +
        w["colocation_density"] * df["C_norm"] +
        w["grid_headroom"]      * (1 - df["H_norm"]) +
        w["renewable_deficit"]  * (1 - df["R_norm"])
    ) * 10   # scale to [0, 10]

    return df.sort_values("dcgsi", ascending=False)


def sensitivity_analysis(df: pd.DataFrame,
                         n_draws: int = 10_000,
                         seed: int = RANDOM_SEED) -> pd.DataFrame:
    """
    Monte Carlo sensitivity: draw weights uniformly from the 4-simplex,
    recompute DCGSI for each draw, and report rank stability statistics.
    """
    np.random.seed(seed)
    components = ["G_norm", "C_norm", "1_minus_H", "1_minus_R"]
    df = df.copy()
    df["1_minus_H"] = 1 - df["H_norm"]
    df["1_minus_R"] = 1 - df["R_norm"]

    baseline_rank = (
        compute_dcgsi(df.drop(columns=["dcgsi"], errors="ignore"))
        .reset_index(drop=True)["market"].tolist()
    )

    rank_agreements = []
    for _ in range(n_draws):
        raw = np.random.dirichlet(np.ones(4))
        w = dict(zip(["demand_growth", "colocation_density",
                      "grid_headroom", "renewable_deficit"], raw))
        ranked = compute_dcgsi(df, weights=w)["market"].tolist()
        top5_agree = sum(ranked[i] == baseline_rank[i]
                         for i in range(min(5, len(ranked))))
        rank_agreements.append(top5_agree)

    return pd.DataFrame({
        "top5_rank_agreement": rank_agreements,
        "pct_full_agreement": [r == 5 for r in rank_agreements],
    }).describe()


def plot_carbon(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    # Panel a: CO2 intensity by market
    ax = axes[0]
    colors = ["#DC2626" if v > 350 else "#D97706" if v > 250 else "#059669"
              for v in df["co2_g_kwh"]]
    bars = ax.barh(df["market"], df["co2_g_kwh"], color=colors, alpha=0.85)
    ax.axvline(df["co2_g_kwh"].mean(), color="#1F2937", linestyle="--",
               linewidth=1.2, label="Market avg.")
    ax.set_xlabel("CO₂ intensity (gCO₂/kWh)", fontsize=9)
    ax.set_title("(a) Grid carbon intensity by data centre market\n(EPA eGRID 2022)",
                 fontsize=9)
    ax.legend(fontsize=8)
    ax.grid(axis="x", linestyle=":", alpha=0.4)

    # Panel b: capacity-weighted contribution
    ax = axes[1]
    ax.barh(df["market"], df["weighted_co2"], color="#2563EB", alpha=0.75)
    ax.set_xlabel("Weighted CO₂ contribution (gCO₂/kWh × share)", fontsize=9)
    ax.set_title("(b) Capacity-weighted CO₂ contribution\nper market",
                 fontsize=9)
    ax.grid(axis="x", linestyle=":", alpha=0.4)

    fig.suptitle("Carbon Intensity Analysis of the US Data Centre Fleet",
                 fontsize=11, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "fig_carbon.pdf"),
                dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved: fig_carbon.pdf")


def plot_dcgsi(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 5))
    palette = plt.cm.RdYlGn_r(np.linspace(0.1, 0.9, len(df)))
    bars = ax.barh(df["market"][::-1], df["dcgsi"][::-1],
                   color=palette, alpha=0.88)
    ax.axvline(df["dcgsi"].median(), color="#1F2937", linestyle="--",
               linewidth=1.2, label=f"Median: {df['dcgsi'].median():.1f}")
    ax.set_xlabel("Data Centre Grid Stress Index (DCGSI, 0–10)", fontsize=9)
    ax.set_title("DCGSI by US Data Centre Market\n"
                 "(equal-weight baseline; see sensitivity in Table 5)", fontsize=10)
    ax.legend(fontsize=8)
    ax.set_xlim(0, 10)
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    for bar, val in zip(bars, df["dcgsi"][::-1]):
        ax.text(val + 0.1, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}", va="center", fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "fig_dcgsi.pdf"),
                dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved: fig_dcgsi.pdf")


if __name__ == "__main__":
    egrid = load_egrid()
    df = merge_egrid(MARKETS, egrid)

    # Carbon analysis
    ca = carbon_analysis(df)
    print(f"\nFleet-average CO₂: {ca['fleet_avg_g_kwh']:.1f} gCO₂/kWh")
    print(f"Counterfactual:    {ca['counterfactual_g_kwh']:.1f} gCO₂/kWh")
    print(f"Potential reduction: {ca['reduction_pct']:.1f}%")
    df.to_csv(os.path.join(RESULTS_DIR, "carbon_analysis.csv"), index=False)
    plot_carbon(df)

    # DCGSI
    df_dcgsi = compute_dcgsi(df)
    print("\nDCGSI scores:")
    print(df_dcgsi[["market", "dcgsi", "G_norm", "C_norm",
                     "H_norm", "R_norm"]].to_string(index=False))
    df_dcgsi.to_csv(os.path.join(RESULTS_DIR, "dcgsi_scores.csv"), index=False)
    plot_dcgsi(df_dcgsi)

    # Sensitivity
    print("\nRunning sensitivity analysis…")
    sens = sensitivity_analysis(df_dcgsi)
    print(sens)
    sens.to_csv(os.path.join(RESULTS_DIR, "dcgsi_sensitivity.csv"))
