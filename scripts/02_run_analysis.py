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
from matplotlib.cm import ScalarMappable
from matplotlib.colors import Normalize
from matplotlib.patches import Ellipse
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.spatial.distance import pdist, squareform
from scipy.stats import bootstrap, chi2
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


def partial_pseudo_f(
    gower: np.ndarray, reduced: np.ndarray, full: np.ndarray
) -> tuple[float, float, float, int, int]:
    """Return partial distance-based pseudo-F and its components."""
    n = len(gower)

    def hat(matrix: np.ndarray) -> np.ndarray:
        return matrix @ np.linalg.pinv(matrix)

    reduced_hat = hat(reduced)
    full_hat = hat(full)
    term_df = int(np.linalg.matrix_rank(full) - np.linalg.matrix_rank(reduced))
    residual_df = int(n - np.linalg.matrix_rank(full))
    term_ss = float(np.trace((full_hat - reduced_hat) @ gower))
    residual_ss = float(np.trace((np.eye(n) - full_hat) @ gower))
    pseudo_f = (term_ss / term_df) / (residual_ss / residual_df)
    return pseudo_f, term_ss, residual_ss, term_df, residual_df


def exact_aggregated_permanova(
    distance: np.ndarray, aggregated: pd.DataFrame
) -> pd.DataFrame:
    """Exact restricted tests on eight independent beach-campaign units."""
    from itertools import permutations, product

    n = len(aggregated)
    centering = np.eye(n) - np.ones((n, n)) / n
    gower = -0.5 * centering @ (distance**2) @ centering
    total_ss = float(np.trace(centering @ gower))
    intercept = np.ones((n, 1))

    def design(beach_values: np.ndarray, season_values: np.ndarray):
        beach = pd.get_dummies(beach_values, drop_first=True, dtype=float).to_numpy()
        season = pd.get_dummies(season_values, drop_first=True, dtype=float).to_numpy()
        return beach, season

    observed_beach = aggregated["beach"].astype(str).to_numpy()
    observed_season = aggregated["season"].astype(str).to_numpy()
    beach_x, season_x = design(observed_beach, observed_season)

    beach_reduced = np.column_stack([intercept, season_x])
    beach_full = np.column_stack([beach_reduced, beach_x])
    beach_stats = partial_pseudo_f(gower, beach_reduced, beach_full)
    beach_null: list[float] = []
    for swaps in product([False, True], repeat=len(SEASON_ORDER)):
        permuted_beach = observed_beach.copy()
        for season, swap in zip(SEASON_ORDER, swaps):
            if swap:
                idx = np.flatnonzero(observed_season == season)
                permuted_beach[idx] = permuted_beach[idx[::-1]]
        perm_beach_x, _ = design(permuted_beach, observed_season)
        perm_full = np.column_stack([beach_reduced, perm_beach_x])
        beach_null.append(partial_pseudo_f(gower, beach_reduced, perm_full)[0])

    season_reduced = np.column_stack([intercept, beach_x])
    season_full = np.column_stack([season_reduced, season_x])
    season_stats = partial_pseudo_f(gower, season_reduced, season_full)
    season_null: list[float] = []
    beach_indices = [
        np.flatnonzero(observed_beach == beach) for beach in BEACH_ORDER
    ]
    for left, right in product(permutations(SEASON_ORDER), repeat=2):
        permuted_season = observed_season.copy()
        permuted_season[beach_indices[0]] = left
        permuted_season[beach_indices[1]] = right
        _, perm_season_x = design(observed_beach, permuted_season)
        perm_full = np.column_stack([season_reduced, perm_season_x])
        season_null.append(partial_pseudo_f(gower, season_reduced, perm_full)[0])

    records = []
    for term, stats, null, scheme in (
        ("beach", beach_stats, beach_null,
         "Exact beach-label swaps within four campaign blocks"),
        ("campaign", season_stats, season_null,
         "Exact campaign-label permutations independently within beaches"),
    ):
        pseudo_f, term_ss, residual_ss, term_df, residual_df = stats
        records.append(
            {
                "term": term,
                "df": term_df,
                "residual_df": residual_df,
                "sum_of_squares": term_ss,
                "partial_r_squared": term_ss / (term_ss + residual_ss),
                "overall_r_squared": term_ss / total_ss,
                "pseudo_f": pseudo_f,
                "p_value": sum(value >= pseudo_f - 1e-12 for value in null) / len(null),
                "exact_permutations": len(null),
                "permutation_scheme": scheme,
            }
        )
    return pd.DataFrame(records)


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


def add_confidence_ellipse(
    ax: plt.Axes,
    x: np.ndarray,
    y: np.ndarray,
    color: str,
    confidence: float = 0.68,
) -> None:
    if len(x) < 3:
        return
    covariance = np.cov(x, y)
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[order]
    eigenvectors = eigenvectors[:, order]
    angle = np.degrees(np.arctan2(eigenvectors[1, 0], eigenvectors[0, 0]))
    radius = np.sqrt(chi2.ppf(confidence, df=2))
    width, height = 2 * radius * np.sqrt(np.maximum(eigenvalues, 0))
    ellipse = Ellipse(
        xy=(float(np.mean(x)), float(np.mean(y))),
        width=float(width),
        height=float(height),
        angle=float(angle),
        facecolor=color,
        edgecolor=color,
        linewidth=1.2,
        alpha=0.14,
        zorder=1,
    )
    ax.add_patch(ellipse)


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
    beach_codes = {"Praia Brava": "BR", "Ilha do Pontal": "IP"}
    season_codes = {
        "Spring": "SPR",
        "Summer": "SUM",
        "Autumn": "AUT",
        "Winter": "WIN",
    }
    scores["sample_id"] = [
        f"{beach_codes.get(beach, str(beach)[:2].upper())}-"
        f"{season_codes.get(season, str(season)[:3].upper())}-T{int(transect)}"
        for beach, season, transect in zip(
            scores["beach"], scores["season"], scores["transect"]
        )
    ]
    scores["sample_label"] = [f"S{i:02d}" for i in range(1, len(scores) + 1)]

    loadings = pd.DataFrame(
        pca.components_[:2].T,
        index=item_columns,
        columns=["PC1_loading", "PC2_loading"],
    ).rename_axis("category").reset_index()
    loadings["PC1_abs_loading"] = loadings["PC1_loading"].abs()
    loadings["PC2_abs_loading"] = loadings["PC2_loading"].abs()
    loading_strength = (
        loadings["PC1_loading"] ** 2 + loadings["PC2_loading"] ** 2
    )
    loadings["contribution_percent"] = 100 * loading_strength / loading_strength.sum()
    scores.to_csv(TABLE_DIR / "table_04_pca_scores_and_clusters.csv", index=False)
    loadings.to_csv(TABLE_DIR / "table_05_pca_loadings.csv", index=False)
    silhouette.to_csv(TABLE_DIR / "table_06_cluster_selection.csv", index=False)

    aggregated = (
        data.groupby(["beach", "season"], observed=True, sort=False)[item_columns]
        .sum()
        .reset_index()
    )
    aggregated["n_transects"] = 3
    aggregated["sampled_area_m2"] = GROUP_AREA_M2
    aggregated["total_items"] = aggregated[item_columns].sum(axis=1)
    aggregated["unit_id"] = [f"U{i:02d}" for i in range(1, len(aggregated) + 1)]
    aggregated_matrix = aggregated[item_columns].to_numpy(dtype=float)
    aggregated_bray = squareform(pdist(aggregated_matrix, metric="braycurtis"))
    exact_permanova = exact_aggregated_permanova(aggregated_bray, aggregated)
    aggregated.to_csv(TABLE_DIR / "table_07_aggregated_units.csv", index=False)
    exact_permanova.to_csv(TABLE_DIR / "table_08_exact_permanova.csv", index=False)
    pd.DataFrame([{
        "term": "beach:campaign",
        "status": "not tested",
        "reason": "One observation per cell gives zero residual degrees of freedom",
    }]).to_csv(TABLE_DIR / "table_09_permutation_scope.csv", index=False)

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

    fig, ax = plt.subplots(figsize=(11, 7.5))
    fig.subplots_adjust(right=0.78)
    for beach in BEACH_ORDER:
        subset = scores[scores["beach"] == beach]
        add_confidence_ellipse(
            ax,
            subset["PC1"].to_numpy(),
            subset["PC2"].to_numpy(),
            PALETTE[beach],
        )
        ax.scatter(
            subset["PC1"],
            subset["PC2"],
            s=72,
            c=PALETTE[beach],
            label=beach,
            alpha=0.95,
            edgecolor="black",
            linewidth=0.6,
            zorder=3,
        )
    plotted_loadings = loadings.nlargest(5, "contribution_percent").copy()
    scale = 0.72 * max(
        np.ptp(scores["PC1"]) / max(np.ptp(loadings["PC1_loading"]), 1e-9),
        np.ptp(scores["PC2"]) / max(np.ptp(loadings["PC2_loading"]), 1e-9),
    )
    contribution_norm = Normalize(
        vmin=float(plotted_loadings["contribution_percent"].min()),
        vmax=float(plotted_loadings["contribution_percent"].max()),
    )
    contribution_cmap = plt.get_cmap("RdYlBu")
    for _, row in plotted_loadings.iterrows():
        x = row["PC1_loading"] * scale
        y = row["PC2_loading"] * scale
        arrow_color = contribution_cmap(
            contribution_norm(row["contribution_percent"])
        )
        ax.annotate(
            "",
            xy=(x, y),
            xytext=(0, 0),
            arrowprops={
                "arrowstyle": "->",
                "color": arrow_color,
                "linewidth": 1.4,
                "alpha": 0.9,
            },
            zorder=4,
        )
        ax.annotate(
            display_label(row["category"]),
            xy=(x, y),
            xytext=(7 if x >= 0 else -7, 6 if y >= 0 else -6),
            textcoords="offset points",
            color=arrow_color,
            fontsize=10,
            fontweight="normal",
            ha="left" if x >= 0 else "right",
            va="bottom" if y >= 0 else "top",
            zorder=5,
        )
    ax.axhline(0, color="black", linewidth=1.0, linestyle=(0, (5, 5)))
    ax.axvline(0, color="black", linewidth=1.0, linestyle=(0, (5, 5)))
    ax.set(
        xlabel=f"PC1 ({100 * pca.explained_variance_ratio_[0]:.1f}%)",
        ylabel=f"PC2 ({100 * pca.explained_variance_ratio_[1]:.1f}%)",
    )
    ax.grid(True, which="major", color="#E3E3E3", linewidth=0.9)
    ax.set_axisbelow(True)
    vector_x = plotted_loadings["PC1_loading"].to_numpy() * scale
    vector_y = plotted_loadings["PC2_loading"].to_numpy() * scale
    combined_x = np.concatenate([scores["PC1"].to_numpy(), vector_x, [0]])
    combined_y = np.concatenate([scores["PC2"].to_numpy(), vector_y, [0]])
    x_padding = max(np.ptp(combined_x) * 0.12, 0.05)
    y_padding = max(np.ptp(combined_y) * 0.12, 0.05)
    ax.set_xlim(combined_x.min() - x_padding, combined_x.max() + x_padding)
    ax.set_ylim(combined_y.min() - y_padding, combined_y.max() + y_padding)
    ax.legend(
        title="Beach",
        bbox_to_anchor=(1.01, 1.0),
        loc="upper left",
        frameon=False,
        fontsize=10,
        title_fontsize=11,
    )
    contribution_map = ScalarMappable(
        norm=contribution_norm, cmap=contribution_cmap
    )
    contribution_map.set_array([])
    colorbar_axis = fig.add_axes([0.835, 0.18, 0.025, 0.32])
    colorbar = fig.colorbar(contribution_map, cax=colorbar_axis)
    colorbar.set_label("Contribution (%)", fontsize=10)
    colorbar.ax.tick_params(labelsize=9)
    save_figure(fig, "figure_03_hellinger_pca")

    cluster_colors = {1: "#F8766D", 2: "#00BFC4", 3: "#7CAE00"}
    cluster_markers = {1: "o", 2: "^", 3: "s"}
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_facecolor("#F4F4F4")
    ax.axhline(0, color="#555555", linewidth=0.9, linestyle="--", zorder=0)
    ax.axvline(0, color="#555555", linewidth=0.9, linestyle="--", zorder=0)
    for cluster_id in sorted(scores["cluster"].unique()):
        subset = scores.loc[scores["cluster"] == cluster_id]
        color = cluster_colors.get(cluster_id, "#666666")
        marker = cluster_markers.get(cluster_id, "D")
        add_confidence_ellipse(
            ax,
            subset["PC1"].to_numpy(),
            subset["PC2"].to_numpy(),
            color=color,
            confidence=0.68,
        )
        ax.scatter(
            subset["PC1"],
            subset["PC2"],
            s=54,
            marker=marker,
            facecolor=color,
            edgecolor="black",
            linewidth=0.55,
            label=f"Cluster {cluster_id}",
            zorder=3,
        )
        for _, row in subset.iterrows():
            ax.annotate(
                row["sample_label"],
                (row["PC1"], row["PC2"]),
                xytext=(4, 5),
                textcoords="offset points",
                color=color,
                fontsize=8.5,
                fontweight="medium",
                zorder=4,
            )
        centroid_x = subset["PC1"].mean()
        centroid_y = subset["PC2"].mean()
        ax.scatter(
            centroid_x,
            centroid_y,
            s=230,
            marker=marker,
            facecolor=color,
            edgecolor="white",
            linewidth=1.3,
            zorder=5,
        )
        ax.scatter(
            centroid_x,
            centroid_y,
            s=230,
            marker=marker,
            facecolor="none",
            edgecolor="black",
            linewidth=0.7,
            zorder=6,
        )
    ax.set(
        xlabel=f"PC1 ({100 * pca.explained_variance_ratio_[0]:.1f}%)",
        ylabel=f"PC2 ({100 * pca.explained_variance_ratio_[1]:.1f}%)",
    )
    ax.grid(True, color="white", linewidth=1.15)
    ax.set_axisbelow(True)
    ax.legend(
        title="K-means cluster",
        loc="upper center",
        bbox_to_anchor=(0.5, -0.12),
        ncol=min(best_k, 3),
        frameon=False,
    )
    fig.subplots_adjust(bottom=0.19)
    save_figure(fig, "figure_06_kmeans_clusters")

    heatmap = (
        data.groupby(["beach", "season"], observed=True)[item_columns]
        .mean()
        .apply(np.log1p)
    )
    heatmap.index = [
        {"Praia Brava": "Praia\nBrava", "Ilha do Pontal": "Ilha do\nPontal"}[beach]
        + "\n" + str(season)
        for beach, season in heatmap.index
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
    ax.set(xlabel="Beach and campaign", ylabel="Item category")
    ax.tick_params(axis="x", rotation=0)
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
    for boundary, label in [(2, "Clean (2–5)"), (5, "Moderately dirty (5–10)"), (10, "Dirty (10–20)"), (20, "Extremely dirty (>20)")]:
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
        "aggregated_permanova": exact_permanova.to_dict(orient="records"),
        "notes": [
            "PCA used Hellinger-transformed relative category abundances.",
            "PERMANOVA used eight aggregated beach-campaign units.",
            "Beach labels were swapped exactly within campaign blocks.",
            "Campaign inference is descriptive because only one annual cycle was sampled.",
            "The beach-by-campaign interaction was not tested because the aggregated model has zero residual degrees of freedom.",
            "Density used 50 m² per transect and CCI used plastic-item density multiplied by 20.",
        ],
    }
    JSON_FILE.write_text(
        json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    perm_beach = exact_permanova.loc[exact_permanova["term"] == "beach"].iloc[0]
    perm_campaign = exact_permanova.loc[exact_permanova["term"] == "campaign"].iloc[0]
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

The three transects in each beach-campaign cell were aggregated before the
inferential analysis, producing eight independent 150-m² units. Exact restricted
Bray–Curtis PERMANOVA tests found:

- Beach, controlling for campaign: pseudo-F = {perm_beach['pseudo_f']:.3f},
  partial R² = {perm_beach['partial_r_squared']:.3f}, p = {perm_beach['p_value']:.4f}
  ({int(perm_beach['exact_permutations'])} exact within-campaign allocations).
- Campaign, controlling for beach: pseudo-F = {perm_campaign['pseudo_f']:.3f},
  partial R² = {perm_campaign['partial_r_squared']:.3f}, p = {perm_campaign['p_value']:.4f}
  ({int(perm_campaign['exact_permutations'])} exact within-beach allocations).

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
"""
    REPORT_FILE.write_text(report, encoding="utf-8")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
