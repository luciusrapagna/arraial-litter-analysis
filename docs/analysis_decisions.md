# Analysis decisions

## AD-001 — Official source

`data/raw/planilha_organizada.xlsx` is the official source for the complete
reanalysis. Values reported in earlier manuscripts are not treated as inputs.

## AD-002 — Sampling unit

Each row is treated as one transect. The design contains three transects within
each beach × season combination. Analyses must retain this replication instead
of aggregating the data to eight rows before estimating uncertainty.

## AD-003 — Language

Repository folders, scripts, variable names, tables, figures, and metadata use
English. Portuguese source labels are preserved through an explicit mapping in
the validation script.

## AD-004 — Sampled area

Each transect represents 50 m². Three transects were sampled per beach × season,
for 150 m² per aggregated beach × season observation. This definition is stated
in the original dissertation draft (`Novo - Esqueleto - Dissertação -
28-06-2020.docx`) and in the earlier analysis report (`PROGRAMA DE PÓS -
útlimas analises feitas 08-05.docx`). It is consistent with the 24-row workbook.
Later manuscript language describing a single 1,000 m² unit conflicts with the
workbook and is not used in this reanalysis.

## AD-005 — Clean Coast Index

CCI is calculated from plastic-item density, not total litter density:
`CCI = (plastic items / sampled area in m²) × 20`. Beach × season CCI values use
the aggregated 150 m² area. Classification thresholds are: very clean (0–2),
clean (2–5), moderately dirty (5–10), dirty (10–20), and extremely dirty (>20).

## Pending decisions

- Confirm whether transects were spatially independent or fixed/revisited.
- Confirm whether season is intended as a descriptive temporal factor or as a
  generalizable seasonal effect from a single annual cycle.
