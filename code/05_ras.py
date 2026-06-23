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
# Load market data from clustering and eGRID
# ------------------------------------------------------------------
from load_data import load_egrid


def load_market_data_ras(cluster_stats_path: str, egrid: pd.DataFrame) -> pd.DataFrame:
    """Load market data from clustering output with renewable fractions."""
    df = pd.read_csv(cluster_stats_path)
    df = df.rename(columns={
        'capacity_gw': 'capacity_gw',
        'share_pct': 'cap_share_pct',
        'label': 'market',
        'top_egrid': 'egrid_subrgn',
    })

    # Merge with eGRID renewable fractions
    egrid_data = egrid[["renewable_frac"]].reset_index()
    egrid_data = egrid_data.rename(columns={"subrgn": "egrid_subrgn"})

    df = df.merge(egrid_data, on="egrid_subrgn", how="left")
    nat_avg_renew = egrid["renewable_frac"].mean()
    df["renewable_frac"] = df["renewable_frac"].fillna(nat_avg_renew)

    return df


def compute_ras(df: pd.DataFrame, egrid: pd.DataFrame) -> pd.DataFrame:
    """Compute RAS for each market.

    RAS = R_m / R_nat
    where R_m is local renewable fraction (market-specific)
    and R_nat is the national renewable fraction from US grid (eGRID average ≈ 22-24%)
    """
    df = df.copy()
    # National renewable fraction from eGRID (US grid average)
    r_nat = egrid["renewable_frac"].mean()

    df["r_nat"] = r_nat
    df["ras"] = df["renewable_frac"] / r_nat

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
        print(f"{row['market']:<22} {row['renewable_frac']:>6.1%}  "
              f"{row['ras']:>5.2f}  {row['alignment']}")

    below = df[df["ras"] < 1.0]
    above = df[df["ras"] >= 1.0]
    print(f"\nMarkets below fleet average: {len(below)}")
    for _, row in below.iterrows():
        deficit_pp = (row["r_nat"] - row["renewable_frac"]) * 100
        print(f"  {row['market']:22}  deficit = {deficit_pp:.1f} pp "
              f"(RAS = {row['ras']:.2f})")


def plot_renewable_alignment(df: pd.DataFrame, nat_avg: float = 0.224):
    """
    Horizontal bar chart: renewable fraction (%) per market vs US national
    average (22.4 %, EIA Table 1.1, 2023).  Markets whose bar falls left of
    the dashed line have below-average renewable penetration.
    """
    # Sort ascending so highest value is at top in barh
    sorted_df = df.sort_values("renewable_frac", ascending=True)

    colors = [
        "#34D399" if v >= nat_avg else "#F87171"
        for v in sorted_df["renewable_frac"]
    ]

    fig, ax = plt.subplots(figsize=(8.5, 5.0))

    bars = ax.barh(
        sorted_df["market"],
        sorted_df["renewable_frac"] * 100,
        color=colors,
        alpha=0.85,
        edgecolor="white",
        linewidth=0.5,
    )

    ax.axvline(nat_avg * 100, color="#1F2937", linestyle="--", linewidth=1.5,
               label=f"US national average ({nat_avg*100:.1f}%, EIA 2023)")

    ax.set_xlabel("Renewable electricity fraction (% of net generation, 2023)",
                  fontsize=9)
    ax.set_title(
        "Renewable electricity fraction by US data centre market (2023)\n"
        "Markets to the left of the dashed line have below-average renewable penetration",
        fontsize=10,
    )

    # Value labels
    for bar, val in zip(bars, sorted_df["renewable_frac"] * 100):
        offset = 0.5
        ax.text(val + offset, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=8)

    # Legend patches
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor="#34D399", alpha=0.85, label="Above national average"),
        Patch(facecolor="#F87171", alpha=0.85, label="Below national average"),
    ]
    handles, _ = ax.get_legend_handles_labels()
    ax.legend(handles=handles + legend_elements, fontsize=8, loc="lower right")

    ax.set_xlim(0, max(sorted_df["renewable_frac"].max() * 100 * 1.18, 30))
    ax.grid(axis="x", linestyle=":", alpha=0.4)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.tight_layout()
    out = os.path.join(FIGURES_DIR, "fig_renewable_alignment.pdf")
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: fig_renewable_alignment.pdf")


if __name__ == "__main__":
    egrid = load_egrid()
    cluster_path = os.path.join(RESULTS_DIR, "cluster_stats.csv")
    markets = load_market_data_ras(cluster_path, egrid)
    df = compute_ras(markets.copy(), egrid)
    r_nat = df["r_nat"].iloc[0]

    print_summary(df, r_nat)

    df.to_csv(os.path.join(RESULTS_DIR, "ras_scores.csv"), index=False)
    print(f"\nSaved: ras_scores.csv")

    plot_ras(df, r_nat)
    plot_renewable_alignment(df)
