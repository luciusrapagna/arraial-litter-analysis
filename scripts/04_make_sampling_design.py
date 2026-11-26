"""Create the publication-ready sampling-design schematic.

At each beach a 75-m alongshore section was divided into 15 contiguous
5 x 10 m sectors. In each campaign three sectors were drawn at random
(without prior inspection of litter abundance) and surveyed as 50-m2
transects extending from the low-tide waterline to 10 m landward.
The selected sectors shown in the figure are illustrative only.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, Patch, Rectangle

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "figures"

INK = "#263238"
SAND = "#F2DEB3"
SEA = "#A9D9E8"
SECTOR_EDGE = "#9C8455"
SEL_FILL = "#E9A86C"
SEL_EDGE = "#A5541B"
EXAMPLE_SELECTED = (3, 8, 12)  # illustrative random draw


def dim_arrow(ax, start, end, text, offset=(0, 0), rotation=0, fontsize=10.5):
    ax.add_patch(FancyArrowPatch(start, end, arrowstyle="<->", mutation_scale=12,
                                 linewidth=1.2, color=INK, zorder=8))
    mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
    ax.text(mx + offset[0], my + offset[1], text, ha="center", va="center",
            rotation=rotation, fontsize=fontsize, color=INK, zorder=9)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})

    fig, ax = plt.subplots(figsize=(12, 6.2))
    ax.set_xlim(-9, 80)
    ax.set_ylim(-9.6, 17.2)
    ax.set_aspect("equal")
    ax.axis("off")

    # Environment: sea below the low-tide waterline, beach above it
    ax.add_patch(Rectangle((-2, -8.2), 79, 8.2, facecolor=SEA, edgecolor="none", zorder=0))
    ax.add_patch(Rectangle((-2, 0), 79, 14.6, facecolor=SAND, edgecolor="none", zorder=0))
    ax.plot([-2, 77], [0, 0], color="#4E8798", linewidth=1.6, zorder=3)
    ax.text(76.5, -7.3, "SEA", ha="right", va="center", fontsize=11, fontweight="bold", color="#24566A")
    ax.text(76.5, 13.7, "BACKSHORE", ha="right", va="center", fontsize=11, fontweight="bold", color="#6C542D")
    ax.text(-1.5, -0.7, "Low-tide waterline", ha="left", va="top", fontsize=10, color="#24566A")

    # Strandline (schematic) inside the sampled strip
    ax.plot([-2, 77], [6.3, 6.3], color="#8A6D3B", linewidth=1.0, linestyle=(0, (1, 2.5)), zorder=2)
    ax.text(-1.5, 6.75, "strandline", ha="left", va="bottom", fontsize=8.5, style="italic", color="#6C542D", zorder=2)

    # 15 contiguous sectors of 5 x 10 m
    for i in range(15):
        x0 = 5 * i
        selected = (i + 1) in EXAMPLE_SELECTED
        ax.add_patch(Rectangle((x0, 0), 5, 10,
                               facecolor=SEL_FILL if selected else "none",
                               alpha=0.75 if selected else 1,
                               edgecolor=SEL_EDGE if selected else SECTOR_EDGE,
                               linewidth=1.8 if selected else 0.9,
                               linestyle="-" if selected else (0, (3, 2)), zorder=4))
        ax.text(x0 + 2.5, 10.7, str(i + 1), ha="center", va="bottom", fontsize=9.5,
                fontweight="bold" if selected else "normal",
                color=SEL_EDGE if selected else "#6C542D", zorder=6)
        if selected:
            ax.text(x0 + 2.5, 3.0, "50 m²", ha="center", va="center", fontsize=9,
                    fontweight="bold", color="#54280D", zorder=6)
    ax.text(37.5, 12.4, "Sector number (1–15)", ha="center", va="bottom", fontsize=9.5, color="#4D3E25")

    # Dimensions
    first_sel = 5 * (EXAMPLE_SELECTED[0] - 1)
    dim_arrow(ax, (first_sel, 7.9), (first_sel + 5, 7.9), "5 m", offset=(0, 0.7), fontsize=9.5)
    dim_arrow(ax, (-2.8, 0), (-2.8, 10), "10 m", offset=(-1.1, 0), rotation=90)
    ax.text(-6.0, 5.0, "Cross-shore", rotation=90, ha="center", va="center", fontsize=9.5, color=INK)
    dim_arrow(ax, (0, -4.6), (75, -4.6), "Sampled coastal section: 75 m alongshore (15 sectors × 5 m)",
              offset=(0, 0.75))

    # Legend
    handles = [
        Patch(facecolor="none", edgecolor=SECTOR_EDGE, linestyle=(0, (3, 2)), label="Sector (5 × 10 m)"),
        Patch(facecolor=SEL_FILL, alpha=0.75, edgecolor=SEL_EDGE,
              label="Randomly selected sector = transect (50 m²)"),
    ]
    leg = ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 1.0), ncol=2,
                    frameon=True, framealpha=0.95, fontsize=9.5)
    leg.get_frame().set_facecolor("#FFFDF7")
    leg.get_frame().set_edgecolor("#C8B893")

    # Summary note
    ax.text(37.5, -9.2,
            "Three sectors drawn at random in each campaign (positions shown are illustrative) · "
            "3 × 50 m² = 150 m² per beach per campaign (20% of the section)",
            ha="center", va="center", fontsize=9, color=INK)

    fig.tight_layout(pad=0.4)
    for suffix in ("png", "pdf", "svg"):
        fig.savefig(OUTPUT / f"figure_method_sampling_design.{suffix}",
                    dpi=400 if suffix == "png" else None, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    main()
