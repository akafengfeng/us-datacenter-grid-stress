# AI-Driven Data Centre Demand Concentration and Renewable Energy Misalignment in the United States

A facility-level spatial analysis of US data centres, introducing the Data Centre Grid Stress Index (DCGSI) and evidence-based siting policy recommendations.

**Authors:** Feng Wei (CAICT)

**Journal:** AIDER — AI-Driven Energy Research

---

## Abstract

The rapid expansion of AI computing has made data centres the fastest-growing source of US grid demand, yet existing literature lacks spatial granularity at the facility level. This study analyzes 98 verified US data centre facilities (10.21 GW total capacity, Q1 2024) using weighted k-means clustering to identify eight distinct regional markets. We introduce the Data Centre Grid Stress Index (DCGSI), a composite metric integrating demand growth, colocation density, transmission constraints, and renewable energy deficits, validated through Monte Carlo sensitivity analysis (10,000 draws).

Key findings: Northern Virginia captures 24.7% of national IT load with a DCGSI score of 9.27/10. Five of eight markets operate below the national renewable fraction baseline (26.4%). State-level OLS regression (n=30, R²=0.89) confirms data centre density as the primary predictor of electricity demand growth. Spatial autocorrelation analysis (Moran's I, p=0.529) indicates no residual clustering effects. We propose a three-tier siting policy framework and quantify facility-level carbon costs.

---

## Repository Contents

```
paper/           Manuscript (main.tex, main.pdf, references.bib)
code/            Analysis pipeline (5 Python scripts)
data/            98 verified facilities dataset
results/         All outputs and generated figures
revision/        Peer review and verification documents
references/      Reference inventory and accessibility verification
```

---

## Reproducibility

### Installation

```bash
pip install -r code/requirements.txt
```

### Running the Analysis

```bash
bash results/reproduce.sh
```

This executes the complete pipeline:
- Data validation
- K-means clustering (silhouette: 0.737, bootstrap CI: [3.0%, 35.0%])
- Carbon intensity and DCGSI analysis
- OLS regression and spatial autocorrelation tests
- Renewable Alignment Score calculations

All results are deterministic (random seed: 42).

---

## Key Results

| Metric | Value |
|--------|-------|
| Facilities analyzed | 98 (10.21 GW) |
| K-means clusters | 8 markets |
| Northern Virginia DCGSI | 9.27 / 10 |
| Fleet average CO₂ intensity | 370.0 gCO₂/kWh |
| Counterfactual CO₂ (renewable-aligned) | 274.7 gCO₂/kWh |
| Reduction potential | 26% |
| National renewable baseline | 26.4% |
| OLS R² (density vs growth) | 0.89 |
| Moran's I p-value | 0.529 |

---

## References

All 17 references verified as real, published works. Complete inventory available in `references/MANIFEST.md`.

---

## Verification

Comprehensive peer review (9/10 quality score) and detailed verification documents available in the `revision/` folder. See `REVISION_LOG.txt` for complete list of corrections and improvements.

---

## License

- Paper: CC-BY 4.0
- Code: MIT
- Data: Public domain (US government sources)

---

**Status:** Publication-ready (June 23, 2026)

**Repository:** https://github.com/akafengfeng/us-datacenter-grid-stress
