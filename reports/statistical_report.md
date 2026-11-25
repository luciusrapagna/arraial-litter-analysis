# Statistical report

## Data basis

The analysis used 24 transects from the official workbook: two beaches, four
seasons, and three transects per beach × season cell. The dataset contains
2,950 recorded items: 2,706 at Praia Brava
and 244 at Ilha do Pontal.

## Composition

The leading categories were:

| Category | Items | Overall composition (%) |
|---|---:|---:|
| expanded_polystyrene | 1,432 | 48.54 |
| plastic | 1,059 | 35.90 |
| rubber_fragments | 145 | 4.92 |
| processed_wood | 80 | 2.71 |
| unidentified | 55 | 1.86 |
| rubber | 41 | 1.39 |

## Density and Clean Coast Index

Each transect represents 50 m², giving 150 m² per beach × season combination.
CCI was calculated as plastic-item density × 20.

         beach season  plastic_items  sampled_area_m2       cci cci_classification
   Praia Brava Spring            133            150.0 17.733333              Dirty
   Praia Brava Summer             89            150.0 11.866667              Dirty
   Praia Brava Autumn             63            150.0  8.400000   Moderately dirty
   Praia Brava Winter            614            150.0 81.866667    Extremely dirty
Ilha do Pontal Spring             53            150.0  7.066667   Moderately dirty
Ilha do Pontal Summer             68            150.0  9.066667   Moderately dirty
Ilha do Pontal Autumn             34            150.0  4.533333              Clean
Ilha do Pontal Winter              5            150.0  0.666667         Very clean

## Multivariate structure

PCA was performed on Hellinger-transformed relative abundances. PC1 explained
40.80% and PC2 explained
22.43% of variance
(63.23% combined).

K-means solutions from k = 2 to 6 were compared with the silhouette score. The
highest score selected k = 3. Clustering is treated as exploratory and
not as evidence of discrete ecological populations.

The three transects in each beach-campaign cell were aggregated before the
inferential analysis, producing eight independent 150-m² units. Exact restricted
Bray–Curtis PERMANOVA tests found:

- Beach, controlling for campaign: pseudo-F = 2.660,
  partial R² = 0.470, p = 0.1250
  (16 exact within-campaign allocations).
- Campaign, controlling for beach: pseudo-F = 2.029,
  partial R² = 0.670, p = 0.0833
  (576 exact within-beach allocations).

The beach × campaign interaction was not tested because the aggregated design
has one observation per cell and therefore zero residual degrees of freedom.
The campaign result describes these four dates and is not evidence of a
general seasonal effect.

## Important limitations

- Only one annual cycle was sampled, so season cannot be cleanly separated from
  unique sampling dates or year-specific events.
- The three transects within each beach × campaign cell are spatial subsamples
  and were aggregated before PERMANOVA.
- The beach test has only 16 exact allocations, so its attainable p-values are
  coarse and inference relies primarily on effect size and ordination.
- One transect contains zero recorded items. It is retained in descriptive and
  multivariate analyses and explicitly represented by a zero Hellinger vector.
- Density and CCI use 50 m² per transect, based on the original dissertation
  methods. The later 1,000 m² manuscript statement is inconsistent with the
  official 24-row workbook and was not used.
