# Data dictionary

The official workbook contains one row per sampled transect. The experimental
structure is two beaches × four seasons × three transects, for 24 observations.

| Variable | Meaning | Type |
|---|---|---|
| `beach` | Sampling beach | Categorical |
| `season` | Sampling season | Categorical |
| `transect` | Transect identifier within beach and season | Integer |
| `plastic` | Count of plastic items | Non-negative integer |
| `expanded_polystyrene` | Count of expanded-polystyrene items | Non-negative integer |
| `rubber` | Count of rubber items | Non-negative integer |
| `glass` | Count of glass items | Non-negative integer |
| `fragments` | Count of fragments | Non-negative integer |
| `fabric` | Count of fabric items | Non-negative integer |
| `processed_wood` | Count of processed-wood items | Non-negative integer |
| `unidentified` | Count of unidentified items | Non-negative integer |
| `personal_care` | Count of personal-care items | Non-negative integer |
| `aluminium` | Count of aluminium items | Non-negative integer |
| `aerosol` | Count of aerosol items | Non-negative integer |
| `rings_caps` | Count of rings and caps | Non-negative integer |
| `total_items` | Sum of all item categories for the transect | Derived integer |

## Translation rule

Only labels and variable names are translated. Observed counts are copied
without alteration from the official workbook.
