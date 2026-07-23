# Statistical report

## Data basis

The analysis used 24 transects from the official workbook: two beaches, four
seasons, and three transects per beach × season cell. The dataset contains
2,921 recorded items: 2,677 at Praia Brava
and 244 at Ilha do Pontal.

## Composition

The leading categories were:

| Category | Items | Overall composition (%) |
|---|---:|---:|
| expanded_polystyrene | 1,432 | 49.02 |
| plastic | 1,059 | 36.25 |
| fragments | 145 | 4.96 |
| processed_wood | 80 | 2.74 |
| unidentified | 55 | 1.88 |
| rubber | 41 | 1.40 |

## Density and Clean Coast Index

Each transect represents 50 m², giving 150 m² per beach × season combination.
CCI was calculated as plastic-item density × 20.

         beach season  plastic_items  sampled_area_m2       cci cci_classification
   Praia Brava Spring            133            150.0 17.733333              Dirty
   Praia Brava Summer             89            150.0 11.866667              Dirty
   Praia Brava Autumn             63            150.0  8.400000   Moderately dirty
   Praia Brava Winter            614            150.0 81.866667    Extremely dirty
Ilha do Pontal Spring             34            150.0  4.533333              Clean
Ilha do Pontal Summer              5            150.0  0.666667         Very clean
Ilha do Pontal Autumn             53            150.0  7.066667   Moderately dirty
Ilha do Pontal Winter             68            150.0  9.066667   Moderately dirty

## Multivariate structure

PCA was performed on Hellinger-transformed relative abundances. PC1 explained
41.19% and PC2 explained
22.76% of variance
(63.95% combined).

K-means solutions from k = 2 to 6 were compared with the silhouette score. The
highest score selected k = 3. Clustering is treated as exploratory and
not as evidence of discrete ecological populations.

Separate Bray–Curtis PERMANOVA tests found:

- Beach: pseudo-F = 3.548, p = 0.0085.
- Season: pseudo-F = 1.195, p = 0.2744.

The sequential balanced factorial PERMANOVA produced:

        term  df  sum_of_squares  r_squared  pseudo_f  p_value  permutations
       beach   1        0.844154   0.138861  4.929152   0.0020          9999
      season   3        0.923849   0.151971  1.798168   0.0523          9999
beach:season   3        1.570989   0.258424  3.057752   0.0014          9999

Dispersion diagnostics (PERMDISP) found:

- Beach: F = 0.309, p = 0.5623.
- Season: F = 0.891, p = 0.3441.

PERMANOVA results must be interpreted together with PERMDISP because a
significant dispersion test can indicate that differences in within-group
variability contribute to the PERMANOVA result.

## Important limitations

- Only one annual cycle was sampled, so season cannot be cleanly separated from
  unique sampling dates or year-specific events.
- The three transects within each beach × season cell provide local replication,
  but their spatial independence must be confirmed.
- One transect contains zero recorded items. It is retained in descriptive and
  multivariate analyses and explicitly represented by a zero Hellinger vector.
- Density and CCI use 50 m² per transect, based on the original dissertation
  methods. The later 1,000 m² manuscript statement is inconsistent with the
  official 24-row workbook and was not used.
