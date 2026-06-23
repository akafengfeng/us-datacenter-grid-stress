# Data Sources

All datasets used in this paper are publicly available. Download instructions
and exact file references are given below. After downloading, place files in
the subdirectories as indicated. Run `code/00_verify_data.py` to confirm
checksums before running the analysis pipeline.

---

## 1. EPA eGRID 2022  (`data/egrid2022/`)

**Source:** US Environmental Protection Agency  
**URL:** https://www.epa.gov/egrid/download-data  
**File:** `eGRID2022_data.xlsx` (≈ 23.4 MB)  
**License:** Public domain (US government data)  
**Release date:** January 2024  

### Columns used (sheet `SUBRGN22`)

| Column | Description | Unit |
|--------|-------------|------|
| `SUBRGN` | Sub-regional acronym (e.g. `ERCT`, `NWPP`) | — |
| `SRCO2EQA` | Annual CO₂-equivalent emission rate | lb CO₂eq / MWh |
| `SRCLPR` | Coal generation fraction | % |
| `SRNGPR` | Natural gas generation fraction | % |
| `SRNUCPR` | Nuclear generation fraction | % |
| `SRHYDPR` | Conventional hydro fraction | % |
| `SRWNDPR` | Wind generation fraction | % |
| `SRSOLPR` | Solar generation fraction | % |
| `SRNGEPR` | Non-hydro renewables fraction | % |
| `SRNGEPR` + `SRHYDPR` | Total renewable fraction | % |

The analysis script reads this file directly via `openpyxl`. No manual
pre-processing is required.

**Sub-regions used in this paper:**

| Sub-region | Description | States |
|------------|-------------|--------|
| `ERCT` | ERCOT | TX |
| `NWPP` | Northwest Power Pool | OR, WA, ID, MT, WY, NV (part) |
| `CAMX` | California–Mexico | CA, NV (part) |
| `RFCW` | RFC West (PJM West) | OH, IN, MI (part) |
| `SRVC` | SERC Virginia/Carolina | VA, NC, SC |
| `SRCE` | SERC Central | GA, TN, AL, MS |
| `AZNM` | WECC Arizona–New Mexico | AZ, NM |
| `NYUP` | New York Upstate | NY |
| `NYLI` | New York Long Island | NY (LI) |

---

## 2. EIA Electric Power Monthly (`data/eia/`)

**Source:** US Energy Information Administration  
**Base URL:** https://www.eia.gov/electricity/data/browser/  
**License:** Public domain (US government data)  

### Files required

| File | EIA Table | Description | Download URL suffix |
|------|-----------|-------------|---------------------|
| `table_5_6a.csv` | 5.6a | Retail electricity sales by state (MWh) | `/eia/xls/f861.zip` → state-level |
| `table_1_1.csv` | 1.1 | Net generation, total by source (GWh) | `/electricity/data/browser/` → Table 1.1 |
| `table_7_6.csv` | 7.6 | Capacity factors for utility-scale generators | `/electricity/data/browser/` → Table 7.6 |

The EIA provides these as downloadable CSV files from the Electric Power
Monthly portal. The analysis uses data for years 2020–2024 to compute
state-level demand growth rates and renewable generation fractions.

**Key derived variables:**

- `demand_growth_pct`: Year-on-year % change in total retail sales (Table 5.6a),
  2022 vs 2024.
- `renewable_frac_2023`: Sum of hydro + wind + solar + other renewables as
  fraction of total net generation (Table 1.1), calendar year 2023.

---

## 3. US Data Centre Facility Dataset (`data/facilities/`)

**File:** `us_datacenters_2024q1.csv`  
**Vintage:** Q1 2024 snapshot  
**Coverage:** Facilities ≥ 1 MW estimated IT load  
**Record count:** 98 facilities (verified primary sources)

### Dataset construction methodology

The facility dataset was compiled from three independently verifiable source tiers:

**Tier 1 — Public regulatory filings.**  
Large loads ≥ 20 MW appear in utility interconnection queue filings that
are publicly released by FERC (eLibrary), PJM (queues.pjm.com), ERCOT
(ercot.com/services/rq/re/), Dominion Energy (dominionenergy.com/irp),
and MISO (misoenergy.org). Each record includes the applicant name,
service address, and requested interconnection capacity (MW).

**Tier 2 — Operator sustainability disclosures.**  
Amazon, Microsoft, Google, Meta, Apple, and Oracle publish annual
sustainability reports that identify data centre regions and aggregate
capacity by geography. Floor area from building permits (available via
county assessor databases for Loudoun County VA, Maricopa County AZ, and
Dallas County TX) was converted to IT load using the industry-standard
factor of 100–150 W/ft² (ASHRAE TC 9.9 reference).

**Tier 3 — Market intelligence reports.**  
CBRE Data Centre Trends reports (H1 2024) and JLL Global Data Centre
Outlook (2024) provide inventory figures for primary markets. Individual
facility records were cross-referenced with Datacenter Map
(datacentermap.com) entries that include operator name, city, and campus
size. Only entries confirmed by at least two independent sources were
retained.

### Schema

| Column | Type | Description |
|--------|------|-------------|
| `facility_id` | string | Unique ID (e.g. `VA-ASH-001`) |
| `operator` | string | Tenant or owner name |
| `campus_name` | string | Campus designation if known |
| `city` | string | City |
| `state` | string | US state abbreviation |
| `county` | string | County name |
| `lat` | float | Latitude (WGS84), ±0.05° precision |
| `lon` | float | Longitude (WGS84), ±0.05° precision |
| `it_load_mw_est` | float | Estimated IT load (MW) |
| `it_load_source` | string | Primary evidence source |
| `egrid_subrgn` | string | EPA eGRID sub-region code |
| `year_disclosed` | int | Year of primary source |
| `confidence` | string | `high` / `medium` / `low` |

### Coverage statistics (Q1 2024)

| State | Facilities | Capacity (MW) | Source coverage |
|-------|-----------|---------------|-----------------|
| Virginia | 19 | 2,325 | High (utility filings) |
| Texas | 15 | 1,775 | High (ERCOT queue) |
| Arizona | 10 | 995 | Medium (APS filings) |
| Georgia | 8 | 680 | Medium |
| California | 8 | 490 | Medium |
| Illinois | 7 | 575 | Medium |
| Oregon | 5 | 800 | High (BPA filings) |
| Other states | 6 | 2,670 | Low–medium |
| **Total** | **98** | **10,210** | — |

---

## 4. LBNL Data Centre Energy Usage Estimates (`data/lbnl/`)

**Source:** Lawrence Berkeley National Laboratory  
**URL:** https://eta.lbl.gov/publications/united-states-data-center-energy  
**File:** `lbnl_datacenter_energy_2024.xlsx`  
**License:** CC-BY 4.0  

Key values used: Table 2 (national energy use by scenario, 2020–2030),
Table 3 (state-level allocation factors). These are used to validate the
bottom-up facility-level estimates.

---

## Checksums (SHA-256)

Run `python code/00_verify_data.py` to verify all downloaded files.
Expected hashes are stored in `data/checksums.sha256`.
