# Analysis decisions

## AD-001 — Official source

`data/raw/planilha_organizada.xlsx` is the official source for the complete
reanalysis. Values reported in earlier manuscripts are not treated as inputs.

## AD-002 — Sampling unit

Each row is one transect, but the three transects within a beach × campaign
combination are spatial subsamples. Descriptive summaries retain all 24 rows.
For PERMANOVA, raw category counts are summed to eight independent 150-m²
beach–campaign units before Bray–Curtis dissimilarities are calculated.

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

## AD-006 — Restricted multivariate inference

The beach effect is tested with all 16 exact beach-label allocations obtained
by swapping labels within the four campaign blocks. The campaign term is tested
with all 576 allocations obtained by independently permuting the four campaign
labels within each beach. The beach × campaign interaction is not tested because
one aggregated observation per cell leaves zero residual degrees of freedom.
Campaign inference is descriptive because only one annual cycle was sampled.

## AD-007 — Correction of the official workbook (November 2026)

The workbook was rebuilt from the field tally sheets (`Dadoa Gerais.xlsx`,
sheets BRAVA and ILHA, transect columns), and checked cell by cell against the
previous version. Three problems
were corrected:

1. Ilha do Pontal season labels were reversed. The ILHA field sheet lists
   campaigns as Winter, Autumn, Spring, Summer, but they had been labelled in the
   Praia Brava order (Summer, Spring, Autumn, Winter). After relabelling, all
   Ilha do Pontal cells match the field sheets exactly; Praia Brava was already
   correct. The superseded file is kept in `data/raw/superseded/`.
2. Metal fragments (field-sheet metal category; 29 items, all at Praia Brava)
   had been omitted. They are now included as `metal_fragments`.
3. The column `Fragmentos` belongs to the rubber category of the field sheet
   (rubber: flip-flops, gloves, tyres, fragments). It is now named
   `rubber_fragments` instead of the ambiguous `fragments`.

Totals after correction: Praia Brava 2,706 items; Ilha do Pontal 244 items;
2,950 items overall.

## Pending decisions

- Confirm whether transects were spatially independent or fixed/revisited.
- Confirm whether season is intended as a descriptive temporal factor or as a
  generalizable seasonal effect from a single annual cycle.
