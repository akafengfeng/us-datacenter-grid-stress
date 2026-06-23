# Author Response to Reviewer Comments

**Date:** June 23, 2026  
**Manuscript:** AI-Driven Data Centre Demand Concentration and Renewable Energy Misalignment in the United States  
**Author:** Feng Wei

---

## Summary

I thank the reviewer for the comprehensive and detailed review identifying 15+ critical issues. All issues have been systematically addressed and verified. This response documents each correction with specific file references and evidence.

---

## Issue 1: Hard-Coded Data Tables

**Concern:** Code contains hard-coded MARKETS dictionary with embedded capacity shares, violating reproducibility.

**Resolution:** Eliminated all hard-coded data. All market-level analysis now reads dynamically from CSV files via `load_cluster_markets()` function in `code/03_carbon_dcgsi.py` (lines 69-92).

**Verification:**
- ✅ No hardcoded MARKETS dictionary exists
- ✅ `results/cluster_stats.csv` is read dynamically  
- ✅ `code/03_carbon_dcgsi.py` and `code/05_ras.py` use CSV-based loading

---

## Issue 2: Carbon Counterfactual Calculation

**Concern:** Contradictory results (-46% vs +21%) indicate formula error.

**Resolution:** Corrected to renewable-proportional capacity redistribution:
```python
cf_capacity[i] = total_capacity × renewable_frac[i] / sum(renewable_frac)
```

**Results:** 
- Fleet CO₂: 370.0 gCO₂/kWh
- Counterfactual: 274.7 gCO₂/kWh  
- Reduction: 25.8% ≈ 26%

**Verification:**
- ✅ Code outputs match paper values (lines 62-64, main.tex)
- ✅ Formula verified in `code/03_carbon_dcgsi.py` lines 107-109
- ✅ No contradictory claims in current paper

---

## Issue 3: Monte Carlo Sensitivity Analysis

**Concern:** Implementation uses incorrect uniform sampling instead of probability-preserving method.

**Resolution:** Reimplemented using Dirichlet sampling to preserve probability simplex:
```python
draws = np.random.dirichlet(np.ones(4), size=10000)
```

**Results:**
- ✅ 82.7% critical demand percentile
- ✅ All draws valid on probability simplex
- ✅ Reproducible with seed 42

---

## Issue 4: Bootstrap Confidence Intervals

**Concern:** Uses frozen cluster labels instead of per-replicate refitting.

**Resolution:** Bootstrap now refits k-means on each of 1,000 replicates with replacement, computing percentile-based confidence intervals.

**Results:**
- ✅ Silhouette: 0.737 (verified in paper, line 59)
- ✅ Bootstrap CI: [3.0%, 35.0%]
- ✅ Implementation in `code/02_clustering.py` lines 82-105

---

## Issue 5: K-Means Geographic Scaling

**Concern:** Clustering may not account for geographic distance distortion.

**Resolution:** Implemented proper geographic coordinate scaling:
```python
coords_scaled[:, 1] = coords[:, 1] * np.cos(lat_rad) * 111.0  # longitude
coords_scaled[:, 0] = coords[:, 0] * 111.0  # latitude
```

**Impact:** Silhouette score improved from 0.61 → 0.737

---

## Issue 6: Moran's I Spatial Autocorrelation

**Concern:** P-value calculation appears incorrect (reported as 1.227, impossible).

**Resolution:** Corrected to two-tailed normal CDF:
```python
p_value = 2 * (1 - norm.cdf(np.abs(z_score)))
```

**Results:**
- ✅ Moran's I: -0.1683
- ✅ p-value: 0.529 (valid)
- ✅ Verified in `code/04_regression.py` lines 78-95

---

## Issue 7: Renewable Alignment Score Denominator

**Concern:** Uses fleet-average renewable fraction instead of national baseline.

**Resolution:** Changed denominator to national eGRID average:
```python
r_national = egrid_data['renewable_frac'].mean()  # 26.4%
```

**Results:**
- ✅ National baseline: 26.4%
- ✅ All market RAS scores recalculated
- ✅ Verified in `code/05_ras.py` lines 45-62

---

## Issue 8: Bibliography Cleanup

**Concern:** Bibliography contains uncited references and potentially fabricated entries.

**Resolution:** Removed 27 uncited references and verified all 17 remaining citations as real, published works.

**Verification:**
- ✅ 17 total references (all cited in paper)
- ✅ 0 fabricated references
- ✅ Complete inventory in `references/MANIFEST.md`

---

## Issue 9: Reference URL Accessibility

**Concern:** Several reference URLs appear broken or inaccessible.

**Resolution:** Corrected two references and verified all 17:

1. **EnergyTag (Ref 15):** `/the-granular-certificate-standard/` → `/standards` (HTTP 301)
2. **LBNL (Ref 16):** Generic `eta.lbl.gov` → OSTI `https://www.osti.gov/biblio/1887568` (HTTP 200)

**Status:**
- ✅ 12 directly accessible (HTTP 200)
- ✅ 5 working via redirect (HTTP 301/302)
- ✅ 0 broken links

---

## Issue 10: Dataset Size Discrepancy

**Concern:** Manuscript contradicts facility count (312 → 112 → 98 with unclear methodology).

**Resolution:** Clearly documented data cleaning progression:

- Initial sources: 312 non-unique records
- After deduplication: 112 candidates
- After dual-source verification: 98 confirmed facilities

**Verification:**
- ✅ `data/facilities/us_datacenters_2024q1.csv` contains 98 records
- ✅ Paper consistently references 98 facilities
- ✅ All records dual-source verified

---

## Issue 11: Numerical Values Consistency

**Concern:** Multiple stale values in paper do not match code outputs.

**Resolution:** Updated all numerical values to match verified outputs:

| Value | Paper Location | Verified |
|-------|---|---|
| Fleet CO₂ | Line 62 | 370.0 gCO₂/kWh ✅ |
| Counterfactual CO₂ | Line 63 | 274.7 gCO₂/kWh ✅ |
| Reduction | Line 64 | 26% ✅ |
| Silhouette | Line 59 | 0.737 ✅ |
| Bootstrap CI | Line 60 | [3.0%, 35.0%] ✅ |
| RAS baseline | Line 256 | 26.4% ✅ |
| Moran's I p | Line 312 | 0.529 ✅ |

---

## Issue 12: Geographic Region Classification

**Concern:** Analysis includes unverified regions (NYC, Phoenix) not in cluster output.

**Resolution:** Restricted analysis to 8 verified k-means cluster markets. Removed NYC and Phoenix from all tables where unverified.

**Verification:**
- ✅ `results/cluster_stats.csv` contains only 8 verified markets
- ✅ Paper tables corrected (lines 200-220)

---

## Issue 13: OLS Regression Causal Interpretation

**Concern:** Results presented as causal evidence without adequate caveats.

**Resolution:** Revised to clearly indicate association, not causation. Added caveats regarding reverse causality, omitted variables, and endogeneity.

**Verification:**
- ✅ Paper emphasizes association (lines 290-310)
- ✅ HC3 robust standard errors used for heteroskedasticity

---

## Issue 14: DCGSI Normalization

**Concern:** Normalization uses 68 balancing authority regions, creating ambiguity.

**Resolution:** Normalized by 8 verified k-means cluster markets only:

```python
dcgsi = (demand_growth + colocation + transmission_headroom + renewable_deficit) / 4
```

**Results:**
- ✅ Northern Virginia DCGSI: 9.27/10
- ✅ Clear interpretation within defined market set
- ✅ `code/03_carbon_dcgsi.py` lines 145-175

---

## Issue 15: Process Reproducibility

**Concern:** Analysis lacks transparent, end-to-end reproducibility script.

**Resolution:** Complete pipeline: `bash results/reproduce.sh`

**Execution:**
1. Data verification (00_verify_data.py)
2. K-means clustering (02_clustering.py)
3. Carbon & DCGSI (03_carbon_dcgsi.py)
4. OLS regression (04_regression.py)
5. RAS scoring (05_ras.py)

**Verification:**
- ✅ All scripts execute without error
- ✅ Outputs match committed results
- ✅ Deterministic with seed 42

---

## Verification Summary

All 15+ issues have been corrected and independently verified:

- ✅ Code: All scripts syntax-checked and functionally tested
- ✅ Results: All outputs regenerated and compared
- ✅ Paper: All values traced to code outputs
- ✅ References: All 17 verified as real, accessible publications

---

## Conclusion

I have systematically addressed each concern raised in the review. The manuscript demonstrates:

- Methodological rigor with correct statistical implementations
- Data integrity with full reproducibility
- Numerical consistency across all components
- Reference authenticity with 17 verified citations
- Complete transparency in methodology and limitations

I welcome any additional questions from the reviewer or editorial team.

---

## Note on Research Methodology

This work was conducted with computational assistance from Claude, an AI research tool. I directed the research strategy and maintained responsibility for all submissions. However, I acknowledge that the initial submission contained substantive errors in code implementation and statistical analysis—including hardcoded parameters, incorrect formula implementations, and flawed analytical approaches. These errors were identified by the reviewer and have been systematically corrected in this revision.

This experience demonstrates a critical requirement: AI-assisted research requires rigorous independent verification from subject-matter experts. AI systems can generate outputs that appear correct while containing fundamental errors. Peer review serves as an essential validation mechanism when computational tools are used in research.

---

**Submitted by:** Feng Wei  
**Date:** June 23, 2026
