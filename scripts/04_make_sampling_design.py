"""Create the publication-ready sampling-design schematic."""

from pathlib import Path

import matplotlib
import numpy as np
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Patch, Polygon, Rectangle


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "figures"


def double_arrow(ax, start, end, text, text_offset=(0, 0), rotation=0):
    arrow = FancyArrowPatch(
        start,
        end,
        arrowstyle="<->",
        mutation_scale=12,
        linewidth=1.25,
        color="#263238",
        zorder=8,
    )
    ax.add_patch(arrow)
    midpoint = ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
    ax.text(
        midpoint[0] + text_offset[0],
        midpoint[1] + text_offset[1],
        text,
        ha="center",
        va="center",
        rotation=rotation,
        fontsize=10,
        color="#263238",
        zorder=9,
    )


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.linewidth": 0,
        }
    )

    fig, ax = plt.subplots(figsize=(12, 6.4))
    ax.set_xlim(-10, 82)
    ax.set_ylim(-4.7, 15.1)
    ax.axis("off")

    shoreline_x = np.linspace(0, 75, 500)
    shoreline_y = (
        0.45
        + 0.32 * np.sin(shoreline_x / 5.6)
        + 0.13 * np.sin(shoreline_x / 1.9)
    )

    land = Polygon(
        np.column_stack(
            [
                np.r_[shoreline_x, 75, 0],
                np.r_[shoreline_y, 13.3, 13.3],
            ]
        ),
        closed=True,
        facecolor="#F2DEB3",
        edgecolor="none",
        zorder=0,
    )
    water = Polygon(
        np.column_stack(
            [
                np.r_[shoreline_x, 75, 0],
                np.r_[shoreline_y, -3.6, -3.6],
            ]
        ),
        closed=True,
        facecolor="#A9D9E8",
        edgecolor="none",
        zorder=0,
    )
    ax.add_patch(land)
    ax.add_patch(water)
    ax.plot(
        shoreline_x,
        shoreline_y,
        color="#FFFFFF",
        linewidth=6,
        solid_capstyle="round",
        zorder=2,
    )
    ax.plot(
        shoreline_x,
        shoreline_y,
        color="#4E8798",
        linewidth=1.2,
        zorder=3,
    )

    ax.text(
        73.5,
        -3.05,
        "SEA",
        ha="right",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#24566A",
    )
    ax.text(
        73.5,
        12.45,
        "BACKSHORE",
        ha="right",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#6C542D",
    )

    upper_y = 10.7
    ax.plot(
        [0, 75],
        [upper_y, upper_y],
        color="#7B6642",
        linewidth=1.3,
        linestyle=(0, (4, 4)),
        zorder=4,
    )
    ax.text(
        37.5,
        11.15,
        "Landward limit of the sampling area",
        ha="center",
        va="bottom",
        fontsize=10.5,
        color="#4D3E25",
    )

    transects = [
        (0, 5, "Transect 1", "0–5 m"),
        (30, 35, "Transect 7", "30–35 m"),
        (60, 65, "Transect 13", "60–65 m"),
    ]
    for x0, x1, label, alongshore in transects:
        y0 = max(
            np.interp(x0, shoreline_x, shoreline_y),
            np.interp(x1, shoreline_x, shoreline_y),
        )
        rect = Rectangle(
            (x0, y0),
            x1 - x0,
            upper_y - y0,
            facecolor="#E9A86C",
            edgecolor="#A5541B",
            linewidth=1.5,
            alpha=0.55,
            zorder=5,
        )
        ax.add_patch(rect)
        ax.plot(
            [x0, x0],
            [y0, upper_y],
            color="#7A3D16",
            linestyle=(0, (3, 3)),
            linewidth=1.25,
            zorder=6,
        )
        ax.plot(
            [x1, x1],
            [y0, upper_y],
            color="#7A3D16",
            linestyle=(0, (3, 3)),
            linewidth=1.25,
            zorder=6,
        )
        ax.text(
            (x0 + x1) / 2,
            8.9,
            f"{label}\n({alongshore})",
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            color="#54280D",
            zorder=8,
        )
        double_arrow(
            ax,
            (x0 + 0.35, 5.15),
            (x1 - 0.35, 5.15),
            "5 m",
            text_offset=(0, 0.48),
        )

    double_arrow(
        ax,
        (-3.2, 0.65),
        (-3.2, upper_y),
        "10 m",
        text_offset=(-1.15, 0),
        rotation=90,
    )
    ax.text(
        -5.45,
        5.7,
        "Cross-shore distance",
        rotation=90,
        ha="center",
        va="center",
        fontsize=9.5,
        color="#263238",
    )

    double_arrow(
        ax,
        (0, -2.35),
        (75, -2.35),
        "Coastal section: 75 m (not to scale)",
        text_offset=(0, 0.65),
    )
    ax.text(
        37.5,
        -0.45,
        "Low-tide water edge",
        ha="center",
        va="top",
        fontsize=10.5,
        color="#24566A",
        bbox={
            "boxstyle": "round,pad=0.25",
            "facecolor": "#EAF7FB",
            "edgecolor": "none",
            "alpha": 0.9,
        },
        zorder=7,
    )

    legend = ax.legend(
        handles=[
            Patch(
                facecolor="#E9A86C",
                edgecolor="#A5541B",
                alpha=0.7,
                label="5 × 10 m sampling unit (50 m²)",
            )
        ],
        loc="upper left",
        bbox_to_anchor=(0.015, 0.985),
        frameon=True,
        framealpha=0.95,
        fontsize=9.5,
    )
    legend.get_frame().set_facecolor("#FFFDF7")
    legend.get_frame().set_edgecolor("#C8B893")

    fig.tight_layout(pad=0.5)
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(
            OUTPUT / f"figure_method_sampling_design.{suffix}",
            dpi=400 if suffix == "png" else None,
            bbox_inches="tight",
            facecolor="white",
        )
    plt.close(fig)


if __name__ == "__main__":
    main()
