# Human Decision Log

This file records significant research decisions made by the author (Feng Wei, CAICT).

---

## Decision 1: Research scope
**Date:** 2026-06-08
**Decision:** Focus on the United States (not global), Q1 2024 snapshot, state-level
and market-level granularity.
**Rationale:** US has the most complete public data on data centre capacity
(regulatory filings, operator disclosures). Global scope would require
significantly different data collection methodology. A Q1 2024 snapshot
represents the most recent period with comprehensive public data.

---

## Decision 2: Facility dataset construction
**Date:** 2026-06-08
**Decision:** Use a three-tier curated dataset (87 regulatory + 143 operator +
82 market records = 312 raw records, 112 confirmed facilities after deduplication)
rather than a commercial database.
**Rationale:** Commercial databases (Data Center Map, DC Byte) are not freely
reproducible. The curated approach uses only public sources (FERC E-3 filings,
operator sustainability reports, SEC disclosures, media market reports) and is
fully documented and reproducible.

---

## Decision 3: DCGSI equal-weight baseline
**Date:** 2026-06-08
**Decision:** Use equal weights (0.25 each) as the DCGSI baseline specification.
**Rationale:** OECD (2008) Handbook on Constructing Composite Indicators
recommends equal weights as the baseline when no empirical calibration dataset
is available. Sensitivity analysis over the full 4-dimensional Dirichlet simplex
(10,000 draws) validates rank stability.

---

## Decision 4: Regression sample
**Date:** 2026-06-08
**Decision:** Use n=30 states (those with >1 documented data centre facility in
the dataset) rather than all 50 states.
**Rationale:** Including states with zero data centres in a regression of demand
growth on DC density would introduce structural zeros and violate the continuous
variable assumption. n=30 represents all states where the causal mechanism
operates.

---

## Decision 5: Policy focus
**Date:** 2026-06-08
**Decision:** Frame policy recommendations around FERC/state PUC jurisdiction,
not federal climate legislation.
**Rationale:** FERC has active rulemaking (Orders 2023, 1920) directly relevant
to interconnection and large-load siting. Federal climate legislation is more
politically uncertain. FERC-focused recommendations are more actionable in the
2024–2026 timeframe.
