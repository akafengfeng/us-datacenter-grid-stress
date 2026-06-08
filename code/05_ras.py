"""
Experiment 4: Renewable Alignment Score (RAS) by data centre market.

RAS_m = R_m / R_nat

where R_m is the local renewable fraction (2023) and R_nat is the
capacity-weighted national average renewable fraction across all markets.

RAS > 1.0: market's renewable share exceeds the national DC fleet average
RAS < 1.0: market is below average (relies on bundled RECs or has temporal
           mismatch between renewable generation and DC demand)

Outputs:
  results/ras_scores.csv
  results/figures/fig_ras.pdf
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from config import *

os.makedirs(FIGURES_DIR, exist_ok=True)

# ------------------------------------------------------------------
# Market data (same as 03_carbon_dcgsi.py; imported here to keep
# each script self-contained and runnable independently)
# Sources: EPA eGRID 2022; NERC 2024 LTRA; utility IRP filings
# ------------------------------------------------------------------
MARKETS = pd.DataFrame([
    ("Northern Virginia", "SRVC",  31.2, 12.4, 0.148),
    ("Dallas–Fort Worth", "ERCT",  15.5,  8.7, 0.348),
    ("Chicago Metro",     "RFCW",   8.5,  4.2, 0.197),
    ("Phoenix",           "AZNM",   7.9,  5.8, 0.124),
    ("Atlanta",           "SRCE",   7.0,  6.3, 0.132),
    ("Pacific Northwest", "NWPP",   5.5,  2.1, 0.721),
    ("SF Bay Area",       "CAMX",   5.4,  2.8, 0.583),
    ("NYC Metro",         "NYUP",   5.0,  3.1, 0.263),
    ("Dispersed",         "RFCE",  14.0,  2.5, 0.220),
], columns=["market", "egrid_subrgn", "cap_share_pct",
            "dc_growth_pct", "renew_frac"])


def compute_ras(df: pd.DataFrame) -> pd.DataFrame:
    """Compute RAS for each market."""
    df = df.copy()
    # Capacity-weighted national renewable fraction
    total_share = df["cap_share_pct"].sum()
    r_nat = (df["renew_frac"] * df["cap_share_pct"]).sum() / total_share

    df["r_nat"] = r_nat
    df["ras"] = df["renew_frac"] / r_nat

    # Alignment category
    df["alignment"] = pd.cut(
        df["ras"],
        bins=[0, 0.5, 0.9, 1.1, 2.0, np.inf],
        labels=["Severely under-aligned",
                "Under-aligned",
                "Near-aligned",
                "Above-aligned",
                "Strongly above-aligned"],
    )
    return df.sort_values("ras", ascending=False)


def plot_ras(df: pd.DataFrame, r_nat: float):
    COLOR_MAP = {
        "Severely under-aligned":  "#DC2626",
        "Under-aligned":           "#F97316",
        "Near-aligned":            "#FBBF24",
        "Above-aligned":           "#34D399",
        "Strongly above-aligned":  "#059669",
    }

    colors = [COLOR_MAP.get(str(a), "#9CA3AF") for a in df["alignment"]]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(df["market"][::-1], df["ras"][::-1],
                   color=colors[::-1], alpha=0.88)

    ax.axvline(1.0, color="#1F2937", linestyle="--", linewidth=1.5,
               label="National DC fleet average (RAS = 1.0)")

    ax.set_xlabel("Renewable Alignment Score (RAS = local / fleet-average renewable fraction)",
                  fontsize=9)
    ax.set_title("Renewable Alignment Score by US Data Centre Market\n"
                 f"(Fleet-average renewable fraction: {r_nat:.1%}; "
                 "RAS < 1 → below-average renewable procurement)",
                 fontsize=10)
    ax.legend(fontsize=8)
    ax.set_xlim(0, max(df["ras"].max() * 1.15, 2.0))
    ax.grid(axis="x", linestyle=":", alpha=0.4)

    for bar, val in zip(bars, df["ras"][::-1]):
        ax.text(val + 0.03, bar.get_y() + bar.get_height() / 2,
                f"{val:.2f}×", va="center", fontsize=8)

    # Legend for alignment categories
    from matplotlib.patches import Patch
    legend_elements = [Patch(facecolor=v, alpha=0.85, label=k)
                       for k, v in COLOR_MAP.items()]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=7.5,
              title="Alignment category", title_fontsize=8)

    fig.tight_layout()
    out = os.path.join(FIGURES_DIR, "fig_ras.pdf")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: fig_ras.pdf")


def print_summary(df: pd.DataFrame, r_nat: float):
    print(f"\nFleet-average renewable fraction: {r_nat:.3f} ({r_nat:.1%})")
    print(f"\n{'Market':<22} {'Renew%':>7} {'RAS':>6} {'Category'}")
    print("-" * 65)
    for _, row in df.iterrows():
        print(f"{row['market']:<22} {row['renew_frac']:>6.1%}  "
              f"{row['ras']:>5.2f}  {row['alignment']}")

    below = df[df["ras"] < 1.0]
    above = df[df["ras"] >= 1.0]
    print(f"\nMarkets below fleet average: {len(below)}")
    for _, row in below.iterrows():
        deficit_pp = (row["r_nat"] - row["renew_frac"]) * 100
        print(f"  {row['market']:22}  deficit = {deficit_pp:.1f} pp "
              f"(RAS = {row['ras']:.2f})")


if __name__ == "__main__":
    df = compute_ras(MARKETS.copy())
    r_nat = df["r_nat"].iloc[0]

    print_summary(df, r_nat)

    df.to_csv(os.path.join(RESULTS_DIR, "ras_scores.csv"), index=False)
    print(f"\nSaved: ras_scores.csv")

    plot_ras(df, r_nat)
