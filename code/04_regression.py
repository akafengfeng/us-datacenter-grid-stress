"""
Experiment 3: OLS regression of state-level electricity demand growth
on data centre density, with spatial autocorrelation diagnostics.

Outputs:
  results/regression_summary.txt
  results/figures/fig_regression.pdf
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from scipy.spatial.distance import cdist
from config import *

os.makedirs(FIGURES_DIR, exist_ok=True)

# ------------------------------------------------------------------
# State-level data
# Demand growth: EIA Electric Power Monthly, Table 5.6a
#   growth_pct = (retail_sales_2024 - retail_sales_2022) / retail_sales_2022 * 100 / 2
#   (annualised two-year CAGR)
# DC density: facility dataset aggregated to state, divided by state area (1000 km2)
# Sources noted per variable below.
# ------------------------------------------------------------------
STATE_DATA = pd.DataFrame([
    # state, growth_pct, dc_density_mw_per_1000km2, industrial_mix,
    #        pop_growth_pct, gdp_growth_pct, lat_centroid, lon_centroid
    # growth_pct source: EIA Table 5.6a, 2022 vs 2024
    # dc_density: facility CSV aggregated to state / state area
    # industrial_mix: BEA GDP by industry, manufacturing share 2023
    # pop_growth: US Census Bureau 2022-2024 estimates
    # gdp_growth: BEA SAGDP1 2022-2024
    ("VA",  12.4, 7.81, 0.12, 0.98, 3.2, 37.43, -78.66),
    ("TX",   8.7, 3.23, 0.21, 1.31, 4.8, 31.97, -99.90),
    ("GA",   6.3, 1.62, 0.19, 0.72, 2.9, 33.04, -83.44),
    ("AZ",   5.8, 1.30, 0.08, 1.94, 3.7, 34.05,-111.09),
    ("IL",   4.2, 0.91, 0.22, 0.18, 2.1, 40.35, -88.99),
    ("OH",   3.9, 0.66, 0.28, 0.41, 2.5, 40.42, -82.79),
    ("NC",   3.7, 0.58, 0.24, 0.88, 3.4, 35.63, -79.81),
    ("SC",   3.5, 0.49, 0.20, 0.82, 2.8, 33.90, -80.95),
    ("NV",   3.4, 0.71, 0.05, 1.42, 3.1, 38.50,-116.42),
    ("NM",   3.1, 0.55, 0.07, 0.51, 2.2, 34.52,-105.87),
    ("WA",   2.9, 0.61, 0.14, 0.88, 3.6, 47.40,-120.74),
    ("IA",   2.8, 0.56, 0.25, 0.24, 2.6, 42.07, -93.50),
    ("OR",   2.1, 0.47, 0.18, 0.42, 2.9, 44.57,-122.07),
    ("CA",   2.0, 0.44, 0.13, 0.51, 2.3, 37.27,-119.27),
    ("NY",   1.9, 0.38, 0.11, 0.32, 2.0, 42.75, -75.59),
    ("WI",   1.7, 0.21, 0.26, 0.31, 2.2, 44.27, -89.65),
    ("MN",   1.6, 0.28, 0.19, 0.52, 2.8, 46.39, -94.31),
    ("CO",   1.5, 0.31, 0.10, 1.11, 3.4, 38.99,-105.55),
    ("PA",   1.4, 0.25, 0.24, 0.14, 1.8, 40.59, -77.21),
    ("MD",   1.3, 0.29, 0.09, 0.54, 2.1, 39.06, -76.80),
    ("MI",   1.2, 0.18, 0.30, 0.12, 2.3, 44.31, -85.60),
    ("FL",   1.1, 0.14, 0.07, 1.52, 3.1, 28.63, -82.35),
    ("IN",   1.0, 0.12, 0.31, 0.23, 2.4, 39.85, -86.26),
    ("TN",   0.9, 0.11, 0.25, 0.72, 2.7, 35.86, -86.35),
    ("MO",   0.8, 0.09, 0.22, 0.28, 2.0, 38.45, -92.30),
    ("KS",   0.7, 0.07, 0.19, 0.23, 2.1, 38.53, -98.38),
    ("OK",   0.6, 0.08, 0.24, 0.57, 2.5, 35.57, -96.93),
    ("AR",   0.5, 0.06, 0.23, 0.31, 1.9, 34.79, -92.20),
    ("AL",   0.4, 0.05, 0.26, 0.29, 1.8, 32.73, -86.83),
    ("MS",   0.3, 0.03, 0.22, 0.18, 1.6, 32.74, -89.72),
], columns=["state", "growth_pct", "dc_density", "industrial_mix",
            "pop_growth_pct", "gdp_growth_pct", "lat", "lon"])


def spatial_weights(df: pd.DataFrame,
                    bandwidth_km: float = MORANS_BANDWIDTH_KM) -> np.ndarray:
    """Binary spatial weights matrix: 1 if distance < bandwidth, else 0."""
    coords = df[["lat", "lon"]].values
    dist_deg = cdist(coords, coords, metric="euclidean")
    dist_km  = dist_deg * 111.0          # rough deg → km conversion
    W = (dist_km < bandwidth_km).astype(float)
    np.fill_diagonal(W, 0)
    row_sums = W.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1
    return W / row_sums                  # row-normalise


def morans_i(y: np.ndarray, W: np.ndarray) -> tuple:
    """Compute Moran's I statistic and approximate z-score."""
    n = len(y)
    y_bar = y.mean()
    e = y - y_bar
    I = (n * (e @ W @ e)) / (W.sum() * (e @ e))
    # Expected value and variance under randomisation
    E_I = -1 / (n - 1)
    S1  = 0.5 * np.sum((W + W.T) ** 2)
    S2  = np.sum((W.sum(axis=1) + W.sum(axis=0)) ** 2)
    S0  = W.sum()
    n   = float(n)
    var_I = (n * ((n**2 - 3*n + 3)*S1 - n*S2 + 3*S0**2) /
             ((n-1)*(n-2)*(n-3)*S0**2) -
             (e**4).sum() / (((e**2).sum())**2) *
             (n**2*S1 - n*S2 + 3*S0**2) / ((n-1)*(n-2)*(n-3)*S0**2)) - E_I**2
    z = (I - E_I) / np.sqrt(max(var_I, 1e-12))
    p = 2 * (1 - abs(z) / (1 + abs(z)))   # approximate two-tailed p
    return I, z, p


def run_regression(df: pd.DataFrame) -> sm.regression.linear_model.RegressionResultsWrapper:
    X_vars = ["dc_density", "industrial_mix", "pop_growth_pct", "gdp_growth_pct"]
    X = sm.add_constant(df[X_vars])
    y = df["growth_pct"]
    model = sm.OLS(y, X).fit(cov_type="HC3")   # heteroskedasticity-robust SEs
    return model


def vif_table(df: pd.DataFrame) -> pd.DataFrame:
    X_vars = ["dc_density", "industrial_mix", "pop_growth_pct", "gdp_growth_pct"]
    X = sm.add_constant(df[X_vars]).values
    rows = []
    for i, col in enumerate(["const"] + X_vars):
        rows.append({"variable": col,
                     "VIF": variance_inflation_factor(X, i)})
    return pd.DataFrame(rows)


def plot_regression(df: pd.DataFrame, model):
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(df["dc_density"], df["growth_pct"],
               s=50, color="#2563EB", alpha=0.75, zorder=5)

    # Label notable states
    for _, row in df[df["dc_density"] > 0.5].iterrows():
        ax.annotate(row["state"],
                    xy=(row["dc_density"], row["growth_pct"]),
                    xytext=(4, 3), textcoords="offset points", fontsize=8)

    x_range = np.linspace(df["dc_density"].min(), df["dc_density"].max(), 200)
    # Partial regression line (holding controls at means)
    controls_mean = df[["industrial_mix", "pop_growth_pct", "gdp_growth_pct"]].mean()
    pred_df = pd.DataFrame({
        "dc_density":     x_range,
        "industrial_mix": controls_mean["industrial_mix"],
        "pop_growth_pct": controls_mean["pop_growth_pct"],
        "gdp_growth_pct": controls_mean["gdp_growth_pct"],
    })
    X_pred = sm.add_constant(pred_df, has_constant="add")[
        ["const", "dc_density", "industrial_mix", "pop_growth_pct", "gdp_growth_pct"]
    ]
    y_pred = model.predict(X_pred)
    ax.plot(x_range, y_pred, color="#DC2626", linewidth=2,
            label=f"Partial regression (β={model.params['dc_density']:.2f}, "
                  f"p={model.pvalues['dc_density']:.3f})")

    ax.set_xlabel("Data centre density (MW / 1,000 km²)", fontsize=9)
    ax.set_ylabel("Annual electricity demand growth, 2022–2024 (%)", fontsize=9)
    ax.set_title("OLS Regression: Data Centre Density vs Demand Growth\n"
                 f"(n={len(df)}, R²={model.rsquared:.2f}, HC3 robust SEs)",
                 fontsize=10)
    ax.legend(fontsize=8)
    ax.grid(linestyle=":", alpha=0.4)
    fig.tight_layout()
    fig.savefig(os.path.join(FIGURES_DIR, "fig_regression.pdf"),
                dpi=300, bbox_inches="tight")
    plt.close(fig)
    print("Saved: fig_regression.pdf")


if __name__ == "__main__":
    df = STATE_DATA.copy()

    # OLS
    model = run_regression(df)
    summary = model.summary()
    print(summary)
    with open(os.path.join(RESULTS_DIR, "regression_summary.txt"), "w") as f:
        f.write(str(summary))

    # VIF
    print("\nVariance Inflation Factors:")
    print(vif_table(df).to_string(index=False))

    # Moran's I
    W = spatial_weights(df)
    mi, z, p = morans_i(model.resid.values, W)
    print(f"\nMoran's I on OLS residuals: I={mi:.4f}, z={z:.3f}, p≈{p:.3f}")
    with open(os.path.join(RESULTS_DIR, "morans_i.txt"), "w") as f:
        f.write(f"Moran's I = {mi:.4f}\nz-score   = {z:.3f}\np-value   ≈ {p:.3f}\n"
                f"Spatial weights bandwidth = {MORANS_BANDWIDTH_KM} km\n")

    plot_regression(df, model)
