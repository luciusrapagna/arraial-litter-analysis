from __future__ import annotations

import json
import os
import warnings
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", str(os.cpu_count() or 1))
warnings.filterwarnings(
    "ignore",
    message="Could not find the number of physical cores",
    category=UserWarning,
)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.spatial.distance import pdist, squareform
from scipy.stats import bootstrap
from skbio import DistanceMatrix
from skbio.stats.distance import permanova, permdisp
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score


ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = ROOT / "data" / "processed" / "marine_litter_tidy.csv"
TABLE_DIR = ROOT / "outputs" / "tables"
FIGURE_DIR = ROOT / "outputs" / "figures"
REPORT_FILE = ROOT / "reports" / "statistical_report.md"
JSON_FILE = ROOT / "reports" / "statistical_results.json"

SEASON_ORDER = ["Spring", "Summer", "Autumn", "Winter"]
BEACH_ORDER = ["Praia Brava", "Ilha do Pontal"]
PALETTE = {"Praia Brava": "#0072B2", "Ilha do Pontal": "#D55E00"}
RANDOM_SEED = 20260723
PERMUTATIONS = 9999
TRANSECT_AREA_M2 = 50.0
GROUP_AREA_M2 = 150.0


def mean_ci(values: pd.Series) -> tuple[float, float]:
    array = values.to_numpy(dtype=float)
    if len(array) < 2 or np.all(array == array[0]):
        return float(array.mean()), float(array.mean())
    result = bootstrap(
        (array,),
        np.mean,
        confidence_level=0.95,
        n_resamples=9999,
        method="BCa",
        random_state=np.random.default_rng(RANDOM_SEED),
    )
    return float(result.confidence_interval.low), float(
        result.confidence_interval.high
    )


def descriptive_table(data: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, float | int | str]] = []
    for (beach, season), group in data.groupby(
        ["beach", "season"], observed=True, sort=False
    ):
        values = group["total_items"]
        ci_low, ci_high = mean_ci(values)
        records.append(
            {
                "beach": beach,
                "season": season,
                "n_transects": int(len(values)),
                "total_items": int(values.sum()),
                "mean_items": float(values.mean()),
                "sd_items": float(values.std(ddof=1)),
                "median_items": float(values.median()),
                "minimum_items": int(values.min()),
                "maximum_items": int(values.max()),
                "mean_95ci_low": ci_low,
                "mean_95ci_high": ci_high,
            }
        )
    return pd.DataFrame(records)


def permanova_result(
    distance_matrix: DistanceMatrix, grouping: pd.Series
) -> dict[str, float | int | str]:
    result = permanova(
        distance_matrix,
        grouping=grouping,
        permutations=PERMUTATIONS,
        seed=RANDOM_SEED,
    )
    return {
        "factor": str(grouping.name),
        "groups": int(result["number of groups"]),
        "pseudo_f": float(result["test statistic"]),
        "p_value": float(result["p-value"]),
        "permutations": int(result["number of permutations"]),
    }


def permdisp_result(
    distance_matrix: DistanceMatrix, grouping: pd.Series
) -> dict[str, float | int | str]:
    result = permdisp(
        distance_matrix,
        grouping=grouping,
        permutations=PERMUTATIONS,
        test="median",
        seed=RANDOM_SEED,
        warn_neg_eigval=False,
    )
    return {
        "factor": str(grouping.name),
        "groups": int(result["number of groups"]),
        "f_value": float(result["test statistic"]),
        "p_value": float(result["p-value"]),
        "permutations": int(result["number of permutations"]),
    }


def cci_classification(value: float) -> str:
    if value <= 2:
        return "Very clean"
    if value <= 5:
        return "Clean"
    if value <= 10:
        return "Moderately dirty"
    if value <= 20:
        return "Dirty"
    return "Extremely dirty"


def factorial_permanova(
    distance: np.ndarray, data: pd.DataFrame
) -> pd.DataFrame:
    n = len(data)
    beach = pd.get_dummies(data["beach"], drop_first=True, dtype=float).to_numpy()
    season = pd.get_dummies(data["season"], drop_first=True, dtype=float).to_numpy()
    interaction = beach * season
    intercept = np.ones((n, 1))
    blocks = [
        ("beach", beach),
        ("season", season),
        ("beach:season", interaction),
    ]
    centering = np.eye(n) - np.ones((n, n)) / n
    gower = -0.5 * centering @ (distance**2) @ centering

    def hat(matrix: np.ndarray) -> np.ndarray:
        return matrix @ np.linalg.pinv(matrix)

    matrices = [intercept]
    projectors = [hat(intercept)]
    for _, block in blocks:
        matrices.append(np.column_stack([matrices[-1], block]))
        projectors.append(hat(matrices[-1]))

    full_projector = projectors[-1]
    residual_projector = np.eye(n) - full_projector
    residual_df = n - np.linalg.matrix_rank(matrices[-1])
    total_ss = float(np.trace(centering @ gower))

    observed: list[dict[str, float | int | str]] = []
    term_matrices: list[np.ndarray] = []
    for index, (name, _) in enumerate(blocks, start=1):
        term_matrix = projectors[index] - projectors[index - 1]
        term_matrices.append(term_matrix)
        term_df = int(
            np.linalg.matrix_rank(matrices[index])
            - np.linalg.matrix_rank(matrices[index - 1])
        )
        term_ss = float(np.trace(term_matrix @ gower))
        residual_ss = float(np.trace(residual_projector @ gower))
        pseudo_f = (term_ss / term_df) / (residual_ss / residual_df)
        observed.append(
            {
                "term": name,
                "df": term_df,
                "sum_of_squares": term_ss,
                "r_squared": term_ss / total_ss,
                "pseudo_f": pseudo_f,
                "p_value": 0.0,
                "permutations": PERMUTATIONS,
            }
        )

    rng = np.random.default_rng(RANDOM_SEED)
    exceedances = np.zeros(len(blocks), dtype=int)
    observed_f = np.array([row["pseudo_f"] for row in observed])
    for _ in range(PERMUTATIONS):
        order = rng.permutation(n)
        permuted = gower[np.ix_(order, order)]
        residual_ss = float(np.trace(residual_projector @ permuted))
        for index, (term_matrix, row) in enumerate(zip(term_matrices, observed)):
            term_ss = float(np.trace(term_matrix @ permuted))
            permuted_f = (term_ss / row["df"]) / (residual_ss / residual_df)
            exceedances[index] += permuted_f >= observed_f[index] - 1e-12

    for index, row in enumerate(observed):
        row["p_value"] = float((exceedances[index] + 1) / (PERMUTATIONS + 1))
    return pd.DataFrame(observed)


def save_figure(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIGURE_DIR / f"{stem}.png", dpi=350, bbox_inches="tight")
    fig.savefig(FIGURE_DIR / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def composition_markdown(table: pd.DataFrame, rows: int = 6) -> str:
    lines = [
        "| Category | Items | Overall composition (%) |",
        "|---|---:|---:|",
    ]
    for _, row in table.head(rows).iterrows():
        lines.append(
            f"| {row['category']} | {int(row['overall_total']):,} | "
            f"{float(row['overall_percent']):.2f} |"
        )
    return "\n".join(lines)


def display_label(value: str) -> str:
    return value.replace("_", " ").title()


def main() -> None:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = pd.read_csv(DATA_FILE)
    data["beach"] = pd.Categorical(
        data["beach"], categories=BEACH_ORDER, ordered=True
    )
    data["season"] = pd.Categorical(
        data["season"], categories=SEASON_ORDER, ordered=True
    )
    id_columns = ["beach", "season", "transect", "total_items"]
    item_columns = [column for column in data.columns if column not in id_columns]
    data["sampled_area_m2"] = TRANSECT_AREA_M2
    data["total_density_items_m2"] = data["total_items"] / TRANSECT_AREA_M2

    table1 = descriptive_table(data)
    table1.to_csv(TABLE_DIR / "table_01_total_items_summary.csv", index=False)

    category_totals = (
        data.groupby("beach", observed=True)[item_columns]
        .sum()
        .T.rename_axis("category")
        .reset_index()
    )
    category_totals["overall_total"] = category_totals[BEACH_ORDER].sum(axis=1)
    category_totals["overall_percent"] = (
        100 * category_totals["overall_total"] / category_totals["overall_total"].sum()
    )
    category_totals = category_totals.sort_values(
        "overall_total", ascending=False
    )
    category_totals.to_csv(
        TABLE_DIR / "table_02_category_composition.csv", index=False
    )

    cci = (
        data.groupby(["beach", "season"], observed=True)
        .agg(
            plastic_items=("plastic", "sum"),
            total_items=("total_items", "sum"),
            n_transects=("transect", "count"),
        )
        .reset_index()
    )
    cci["sampled_area_m2"] = cci["n_transects"] * TRANSECT_AREA_M2
    cci["total_density_items_m2"] = cci["total_items"] / cci["sampled_area_m2"]
    cci["plastic_density_items_m2"] = (
        cci["plastic_items"] / cci["sampled_area_m2"]
    )
    cci["cci"] = 20 * cci["plastic_density_items_m2"]
    cci["cci_classification"] = cci["cci"].map(cci_classification)
    cci.to_csv(TABLE_DIR / "table_03_density_and_cci.csv", index=False)

    beach_totals = (
        data.groupby("beach", observed=True)["total_items"].sum().astype(int).to_dict()
    )
    grand_total = int(data["total_items"].sum())

    matrix = data[item_columns].to_numpy(dtype=float)
    row_totals = matrix.sum(axis=1)
    relative = np.divide(
        matrix,
        row_totals[:, None],
        out=np.zeros_like(matrix),
        where=row_totals[:, None] != 0,
    )
    hellinger = np.sqrt(relative)
    pca = PCA(n_components=min(len(item_columns), len(data)), random_state=RANDOM_SEED)
    scores_array = pca.fit_transform(hellinger)
    scores = data[["beach", "season", "transect", "total_items"]].copy()
    scores["PC1"] = scores_array[:, 0]
    scores["PC2"] = scores_array[:, 1]
    scores["cluster"] = -1

    silhouette_records: list[dict[str, float | int]] = []
    fitted_clusters: dict[int, np.ndarray] = {}
    for k in range(2, 7):
        model = KMeans(n_clusters=k, n_init=100, random_state=RANDOM_SEED)
        labels = model.fit_predict(hellinger)
        fitted_clusters[k] = labels
        silhouette_records.append(
            {"k": k, "silhouette_score": float(silhouette_score(hellinger, labels))}
        )
    silhouette = pd.DataFrame(silhouette_records)
    best_k = int(
        silhouette.loc[silhouette["silhouette_score"].idxmax(), "k"]
    )
    scores["cluster"] = fitted_clusters[best_k] + 1

    loadings = pd.DataFrame(
        pca.components_[:2].T,
        index=item_columns,
        columns=["PC1_loading", "PC2_loading"],
    ).rename_axis("category").reset_index()
    loadings["PC1_abs_loading"] = loadings["PC1_loading"].abs()
    loadings["PC2_abs_loading"] = loadings["PC2_loading"].abs()
    scores.to_csv(TABLE_DIR / "table_04_pca_scores_and_clusters.csv", index=False)
    loadings.to_csv(TABLE_DIR / "table_05_pca_loadings.csv", index=False)
    silhouette.to_csv(TABLE_DIR / "table_06_cluster_selection.csv", index=False)

    bray = squareform(pdist(matrix, metric="braycurtis"))
    ids = [f"S{i + 1:02d}" for i in range(len(data))]
    distance_matrix = DistanceMatrix(bray, ids=ids)
    beach_group = pd.Series(data["beach"].astype(str).to_numpy(), index=ids, name="beach")
    season_group = pd.Series(
        data["season"].astype(str).to_numpy(), index=ids, name="season"
    )
    permanova_results = [
        permanova_result(distance_matrix, beach_group),
        permanova_result(distance_matrix, season_group),
    ]
    permdisp_results = [
        permdisp_result(distance_matrix, beach_group),
        permdisp_result(distance_matrix, season_group),
    ]
    factorial = factorial_permanova(bray, data)
    pd.DataFrame(permanova_results).to_csv(
        TABLE_DIR / "table_07_one_factor_permanova.csv", index=False
    )
    pd.DataFrame(permdisp_results).to_csv(
        TABLE_DIR / "table_08_permdisp.csv", index=False
    )
    factorial.to_csv(TABLE_DIR / "table_09_factorial_permanova.csv", index=False)

    sns.set_theme(style="whitegrid", context="talk")

    plot_data = data.copy()
    plot_data["log1p_total_items"] = np.log1p(plot_data["total_items"])
    fig, ax = plt.subplots(figsize=(10, 6.5))
    sns.stripplot(
        data=plot_data,
        x="season",
        y="log1p_total_items",
        hue="beach",
        hue_order=BEACH_ORDER,
        palette=PALETTE,
        dodge=True,
        jitter=0.08,
        size=8,
        alpha=0.85,
        ax=ax,
    )
    sns.pointplot(
        data=plot_data,
        x="season",
        y="log1p_total_items",
        hue="beach",
        hue_order=BEACH_ORDER,
        palette=PALETTE,
        dodge=0.35,
        estimator=np.median,
        errorbar=("pi", 50),
        markers="D",
        linestyles="-",
        ax=ax,
    )
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles[:2],
        labels[:2],
        title="Beach",
        frameon=True,
        loc="lower left",
        bbox_to_anchor=(0.01, 0.03),
    )
    raw_ticks = np.array([0, 1, 3, 10, 30, 100, 300, 1000])
    ax.set_yticks(np.log1p(raw_ticks))
    ax.set_yticklabels([f"{value:,}" for value in raw_ticks])
    ax.set(xlabel="", ylabel="Marine-litter items per transect")
    ax.text(
        0.01,
        0.98,
        "Points: transects; diamonds: medians; bars: interquartile ranges",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=10,
    )
    save_figure(fig, "figure_01_total_items_by_season")

    composition = (
        data.groupby(["beach", "season"], observed=True)[item_columns].sum()
        .reset_index()
        .melt(
            id_vars=["beach", "season"],
            var_name="category",
            value_name="items",
        )
    )
    composition["percent"] = composition.groupby(
        ["beach", "season"], observed=True
    )["items"].transform(lambda values: 100 * values / values.sum())
    top_categories = (
        composition.groupby("category")["items"].sum().nlargest(7).index
    )
    composition["display_category"] = np.where(
        composition["category"].isin(top_categories),
        composition["category"],
        "other_categories",
    )
    plot_composition = (
        composition.groupby(
            ["beach", "season", "display_category"], observed=True
        )["percent"].sum().reset_index()
    )
    plot_composition["display_category"] = plot_composition[
        "display_category"
    ].map(display_label)
    fig, axes = plt.subplots(1, 2, figsize=(15, 6.5), sharey=True)
    category_palette = sns.color_palette(
        "colorblind", n_colors=plot_composition["display_category"].nunique()
    )
    for ax, beach in zip(axes, BEACH_ORDER):
        pivot = (
            plot_composition[plot_composition["beach"] == beach]
            .pivot(index="season", columns="display_category", values="percent")
            .reindex(SEASON_ORDER)
            .fillna(0)
        )
        pivot.plot(
            kind="bar",
            stacked=True,
            color=category_palette,
            width=0.78,
            ax=ax,
        )
        ax.set(title=beach, xlabel="", ylabel="Composition (%)")
        ax.tick_params(axis="x", rotation=0)
        if ax is axes[0]:
            ax.get_legend().remove()
        else:
            ax.legend(
                title="Category",
                bbox_to_anchor=(1.02, 1),
                loc="upper left",
                fontsize=9,
            )
    save_figure(fig, "figure_02_composition_by_beach_and_season")

    fig, ax = plt.subplots(figsize=(10, 7))
    for beach in BEACH_ORDER:
        subset = scores[scores["beach"] == beach]
        ax.scatter(
            subset["PC1"],
            subset["PC2"],
            s=95,
            c=PALETTE[beach],
            label=beach,
            alpha=0.85,
            edgecolor="white",
            linewidth=0.7,
        )
    top_loading_categories = set(
        loadings.nlargest(5, "PC1_abs_loading")["category"]
    ) | set(loadings.nlargest(5, "PC2_abs_loading")["category"])
    scale = 0.85 * max(
        np.ptp(scores["PC1"]) / max(np.ptp(loadings["PC1_loading"]), 1e-9),
        np.ptp(scores["PC2"]) / max(np.ptp(loadings["PC2_loading"]), 1e-9),
    )
    for _, row in loadings[
        loadings["category"].isin(top_loading_categories)
    ].iterrows():
        x = row["PC1_loading"] * scale
        y = row["PC2_loading"] * scale
        ax.arrow(
            0,
            0,
            x,
            y,
            color="#333333",
            alpha=0.65,
            width=0.001,
            head_width=0.015,
            length_includes_head=True,
        )
        ax.text(x * 1.06, y * 1.06, display_label(row["category"]), fontsize=9)
    ax.axhline(0, color="#999999", linewidth=0.8)
    ax.axvline(0, color="#999999", linewidth=0.8)
    ax.set(
        xlabel=f"PC1 ({100 * pca.explained_variance_ratio_[0]:.1f}%)",
        ylabel=f"PC2 ({100 * pca.explained_variance_ratio_[1]:.1f}%)",
    )
    ax.legend(title="Beach")
    save_figure(fig, "figure_03_hellinger_pca")

    heatmap = (
        data.groupby(["beach", "season"], observed=True)[item_columns]
        .mean()
        .apply(np.log1p)
    )
    heatmap.index = [
        (display_label(beach), str(season)) for beach, season in heatmap.index
    ]
    heatmap.columns = [display_label(column) for column in heatmap.columns]
    fig, ax = plt.subplots(figsize=(13, 7))
    sns.heatmap(
        heatmap.T,
        cmap="mako",
        linewidths=0.4,
        linecolor="white",
        cbar_kws={"label": "log(1 + mean item count)"},
        ax=ax,
    )
    ax.set(xlabel="Beach × season", ylabel="Item category")
    save_figure(fig, "figure_04_category_heatmap")

    fig, ax = plt.subplots(figsize=(11, 6.5))
    sns.barplot(
        data=cci,
        x="season",
        y="cci",
        hue="beach",
        hue_order=BEACH_ORDER,
        palette=PALETTE,
        ax=ax,
    )
    for boundary, label in [(2, "Very clean"), (5, "Clean"), (10, "Moderate"), (20, "Dirty")]:
        ax.axhline(boundary, color="#555555", linestyle="--", linewidth=0.8)
        ax.text(3.48, boundary * 1.03, label, ha="right", va="bottom", fontsize=9)
    ax.set_yscale("log")
    ax.set(xlabel="", ylabel="Clean Coast Index (CCI)")
    ax.legend(title="Beach")
    save_figure(fig, "figure_05_clean_coast_index")

    results = {
        "grand_total": grand_total,
        "beach_totals": {str(key): int(value) for key, value in beach_totals.items()},
        "pca_explained_variance_percent": {
            "PC1": float(100 * pca.explained_variance_ratio_[0]),
            "PC2": float(100 * pca.explained_variance_ratio_[1]),
            "PC1_plus_PC2": float(100 * pca.explained_variance_ratio_[:2].sum()),
        },
        "best_k": best_k,
        "transect_area_m2": TRANSECT_AREA_M2,
        "cci": cci.assign(
            beach=cci["beach"].astype(str), season=cci["season"].astype(str)
        ).to_dict(orient="records"),
        "permanova": permanova_results,
        "permdisp": permdisp_results,
        "factorial_permanova": factorial.to_dict(orient="records"),
        "notes": [
            "PCA used Hellinger-transformed relative category abundances.",
            "PERMANOVA tests beach and season separately and is exploratory.",
            "PERMDISP must be considered when interpreting PERMANOVA.",
            "Density used 50 m² per transect and CCI used plastic-item density multiplied by 20.",
        ],
    }
    JSON_FILE.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    perm_beach, perm_season = permanova_results
    disp_beach, disp_season = permdisp_results
    report = f"""# Statistical report

## Data basis

The analysis used 24 transects from the official workbook: two beaches, four
seasons, and three transects per beach × season cell. The dataset contains
{grand_total:,} recorded items: {beach_totals['Praia Brava']:,} at Praia Brava
and {beach_totals['Ilha do Pontal']:,} at Ilha do Pontal.

## Composition

The leading categories were:

{composition_markdown(category_totals)}

## Density and Clean Coast Index

Each transect represents 50 m², giving 150 m² per beach × season combination.
CCI was calculated as plastic-item density × 20.

{cci[['beach', 'season', 'plastic_items', 'sampled_area_m2', 'cci', 'cci_classification']].to_string(index=False)}

## Multivariate structure

PCA was performed on Hellinger-transformed relative abundances. PC1 explained
{100 * pca.explained_variance_ratio_[0]:.2f}% and PC2 explained
{100 * pca.explained_variance_ratio_[1]:.2f}% of variance
({100 * pca.explained_variance_ratio_[:2].sum():.2f}% combined).

K-means solutions from k = 2 to 6 were compared with the silhouette score. The
highest score selected k = {best_k}. Clustering is treated as exploratory and
not as evidence of discrete ecological populations.

Separate Bray–Curtis PERMANOVA tests found:

- Beach: pseudo-F = {perm_beach['pseudo_f']:.3f}, p = {perm_beach['p_value']:.4f}.
- Season: pseudo-F = {perm_season['pseudo_f']:.3f}, p = {perm_season['p_value']:.4f}.

The sequential balanced factorial PERMANOVA produced:

{factorial.to_string(index=False)}

Dispersion diagnostics (PERMDISP) found:

- Beach: F = {disp_beach['f_value']:.3f}, p = {disp_beach['p_value']:.4f}.
- Season: F = {disp_season['f_value']:.3f}, p = {disp_season['p_value']:.4f}.

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
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
