# Paper Plan

## Status: COMPLETE — Submitted to AIDER

---

## Research Question

How is US data centre electricity demand spatially distributed across grid regions,
and what is the magnitude of misalignment between data centre siting and local
renewable energy availability?

## Novelty

No existing study simultaneously addresses:
1. Facility-level spatial clustering of US data centre capacity
2. A composite grid stress index (DCGSI) integrating demand growth, colocation
   density, transmission headroom, and renewable deficit
3. Renewable alignment scoring at the market level
4. HC3-robust OLS regression with Moran's I spatial diagnostics linking DC density
   to state-level electricity demand growth

## Experiment Contract

| # | Experiment | Method | Output |
|---|-----------|--------|--------|
| 1 | Spatial clustering | Weighted k-means (k=8, k-means++, 20 restarts, seed=42) with 2,000-draw bootstrap CIs | cluster_stats.csv, fig_clusters.pdf |
| 2 | Carbon intensity | Capacity-weighted fleet average from EPA eGRID 2022 sub-regional rates | carbon_analysis.csv, fig_carbon.pdf |
| 3 | Demand growth regression | OLS n=30 states, HC3 robust SEs, VIF table, Moran's I | regression_summary.txt, fig_regression.pdf |
| 4 | Renewable Alignment Score | RAS_m = R_m / R_nat | ras_scores.csv, fig_ras.pdf |
| 5 | DCGSI + sensitivity | Equal-weight composite, 10,000-draw Dirichlet Monte Carlo | dcgsi_scores.csv, fig_dcgsi.pdf |

## Key Parameters

- Facility dataset: 112 confirmed records, Q1 2024
- eGRID version: 2022 (EPA, SUBRGN22 sheet)
- k-means clusters: k=8 (elbow + silhouette validated)
- Random seed: 42 (all stochastic operations)
- DCGSI weights: 0.25 each (OECD 2008 equal-weight baseline)
- Regression sample: n=30 states with ≥1 documented facility
- Spatial weights bandwidth: 500 km (Moran's I)

## Status

- [x] Director framed research question
- [x] Librarian verified literature gap
- [x] Librarian built references.bib (35+ references)
- [x] Worker implemented all 5 experiments
- [x] Worker wrote full LaTeX manuscript
- [x] Judge review: methodology sound, no shortcuts detected
- [x] Statistician review: HC3 SEs, VIF, Moran's I, bootstrap CIs
- [x] Illustrator review: all figures from Python (no hardcoded data)
- [x] Editor review: LaTeX compiles, references real, numbers consistent
- [x] REPRODUCIBILITY.md completed
- [x] Submitted to AIDER
