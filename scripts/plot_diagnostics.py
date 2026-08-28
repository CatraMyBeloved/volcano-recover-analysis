"""Render inspection figures for the composites, change maps and clusters.

These are diagnostics, not the portfolio figure. The priority is seeing what the
data actually says, including where it is thin, so gaps are drawn in grey rather
than interpolated away and every panel that should be comparable shares a scale.

Usage:
    uv run scripts/plot_diagnostics.py [--index ndvi]
"""
import argparse
from pathlib import Path

import matplotlib

matplotlib.use('Agg')

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap


import src  # noqa: F401  (repairs the PROJ search path before rasterio loads)
import rasterio

RESULTS = Path(__file__).parents[1] / 'results' / 'analysis_results'
FIGURES = Path(__file__).parents[1] / 'results' / 'figures'

PERIODS = ['baseline', 'impact', 'recovery']
PERIOD_TITLES = {
    'baseline': 'Baseline\n2018 and 2019, Feb to Apr',
    'impact': 'Impact\n2022, Feb to Apr',
    'recovery': 'Recovery\n2025, Feb to Apr',
}

GAP = '#d9d9d9'


def load(name: str) -> tuple[np.ndarray, tuple[float, float, float, float]]:
    path = RESULTS / name
    if not path.exists():
        raise SystemExit(f'Missing {path}. Run scripts/build_composites.py first.')
    with rasterio.open(path) as src_raster:
        data = src_raster.read(1)
        bounds = src_raster.bounds
    # Axes in kilometres; UTM metres make for unreadable tick labels.
    extent = (bounds.left / 1000, bounds.right / 1000,
              bounds.bottom / 1000, bounds.top / 1000)
    return data, extent


def show(ax, data, extent, cmap, vmin, vmax, title):
    palette = plt.get_cmap(cmap).copy()
    palette.set_bad(GAP)
    image = ax.imshow(
        np.ma.masked_invalid(data), extent=extent, origin='upper',
        cmap=palette, vmin=vmin, vmax=vmax, interpolation='nearest',
    )
    ax.set_title(title, fontsize=10)
    ax.tick_params(labelsize=7)
    return image


def figure_composites(index: str) -> Path:
    """Composites on one shared scale, with the observation depth beneath."""
    fig, axes = plt.subplots(2, 3, figsize=(13, 8.6), constrained_layout=True)

    medians = [load(f'{period}_{index}_{"median"}.tif') for period in PERIODS]
    counts = [load(f'{period}_{index}_count.tif') for period in PERIODS]
    count_max = max(int(np.nanmax(data)) for data, _ in counts)

    for column, period in enumerate(PERIODS):
        data, extent = medians[column]
        image = show(axes[0, column], data, extent, 'YlGn', -0.1, 0.85,
                     PERIOD_TITLES[period])
        if column == 2:
            fig.colorbar(image, ax=axes[0, :], shrink=0.8,
                         label=f'{index.upper()} (median)')

        data, extent = counts[column]
        depth = show(axes[1, column], data, extent, 'cividis', 0, count_max,
                     f'clear observations, {period}')
        if column == 2:
            fig.colorbar(depth, ax=axes[1, :], shrink=0.8,
                         label='scenes contributing')

    for ax in axes.flat:
        ax.set_xlabel('UTM 28N easting (km)', fontsize=7)
    for ax in axes[:, 0]:
        ax.set_ylabel('northing (km)', fontsize=7)

    fig.suptitle(
        f'{index.upper()} median composites and observation depth · '
        'grey is no clear observation',
        fontsize=12,
    )
    path = FIGURES / f'composites_{index}.png'
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def figure_change(index: str) -> Path:
    """Impact against baseline, and recovery against impact."""
    baseline, extent = load(f'baseline_{index}_median.tif')
    impact, _ = load(f'impact_{index}_median.tif')
    recovery, _ = load(f'recovery_{index}_median.tif')

    panels = [
        (impact - baseline, 'Impact minus baseline\nred is vegetation lost'),
        (recovery - impact, 'Recovery minus impact\nblue is vegetation regained'),
        (recovery - baseline, 'Recovery minus baseline\nred is still below pre-eruption'),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 5.2), constrained_layout=True)
    for ax, (data, title) in zip(axes, panels):
        # One symmetric scale across all three panels, so the same colour means
        # the same magnitude of change in each.
        image = show(ax, data, extent, 'RdBu', -0.6, 0.6, title)
        ax.set_xlabel('UTM 28N easting (km)', fontsize=7)
    axes[0].set_ylabel('northing (km)', fontsize=7)
    fig.colorbar(image, ax=axes, shrink=0.85, label=f'change in {index.upper()}')
    fig.suptitle(f'Change in {index.upper()} between period composites', fontsize=12)

    path = FIGURES / f'change_{index}.png'
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def figure_clusters(index: str, n_clusters: int = 5) -> Path | None:
    """Cluster map beside the trajectory each cluster represents."""
    path_in = RESULTS / f'clusters_{index}_{n_clusters}.tif'
    if not path_in.exists():
        print(f'  no cluster raster at {path_in}, skipping')
        return None

    labels, extent = load(path_in.name)
    labels = np.where(labels < 0, np.nan, labels)

    # Sequential, because the clusters are ordered by baseline greenness and so
    # have a natural low-to-high reading rather than being categories.
    colours = ['#8c510a', '#d8b365', '#f6e8c3', '#80cdc1', '#01665e'][:n_clusters]
    cmap = ListedColormap(colours)
    cmap.set_bad(GAP)
    norm = BoundaryNorm(np.arange(-0.5, n_clusters, 1), cmap.N)

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 5.6), constrained_layout=True,
                             gridspec_kw={'width_ratios': [1.25, 1]})

    image = axes[0].imshow(
        np.ma.masked_invalid(labels), extent=extent, origin='upper',
        cmap=cmap, norm=norm, interpolation='nearest',
    )
    axes[0].set_title('Recovery pattern clusters\ngrey is missing in some period',
                      fontsize=10)
    axes[0].set_xlabel('UTM 28N easting (km)', fontsize=7)
    axes[0].set_ylabel('northing (km)', fontsize=7)
    axes[0].tick_params(labelsize=7)
    bar = fig.colorbar(image, ax=axes[0], ticks=range(n_clusters), shrink=0.85)
    bar.set_label('cluster')

    for number in range(n_clusters):
        mask = labels == number
        if not mask.any():
            continue
        series = []
        for period in PERIODS:
            data, _ = load(f'{period}_{index}_median.tif')
            series.append(np.nanmedian(data[mask]))
        axes[1].plot(range(3), series, marker='o', color=colours[number],
                     linewidth=2, label=f'cluster {number}')

    axes[1].set_xticks(range(3))
    axes[1].set_xticklabels(['baseline', 'impact', 'recovery'])
    axes[1].set_ylabel(f'median {index.upper()}')
    axes[1].set_title('Cluster trajectories', fontsize=10)
    axes[1].axhline(0, color='#999999', linewidth=0.8)
    axes[1].legend(fontsize=8, frameon=False)
    axes[1].grid(axis='y', alpha=0.3)

    path = FIGURES / f'clusters_{index}.png'
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def figure_distributions(index: str) -> Path:
    """Where the change sits, and how much area each magnitude covers."""
    baseline, _ = load(f'baseline_{index}_median.tif')
    impact, _ = load(f'impact_{index}_median.tif')
    recovery, _ = load(f'recovery_{index}_median.tif')
    change = impact - baseline
    finite = change[np.isfinite(change)]

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.4), constrained_layout=True)

    axes[0].hist(finite, bins=160, color='#4a6fa5')
    axes[0].axvline(0, color='#333333', linewidth=1)
    axes[0].axvline(-0.3, color='#b2182b', linewidth=1, linestyle='--',
                    label='0.3 loss threshold')
    axes[0].set_xlabel(f'impact minus baseline {index.upper()}')
    axes[0].set_ylabel('pixels')
    axes[0].set_title('Distribution of change across the window', fontsize=10)
    axes[0].legend(fontsize=8, frameon=False)

    # Area beyond each loss threshold, at 10 m pixels, so 100 pixels is a
    # hectare and 10000 is a square kilometre.
    thresholds = np.arange(0.05, 0.75, 0.025)
    areas = [np.count_nonzero(finite < -t) / 10000 for t in thresholds]
    axes[1].plot(thresholds, areas, color='#b2182b', linewidth=2)
    axes[1].set_xlabel(f'{index.upper()} loss threshold')
    axes[1].set_ylabel('area beyond threshold (km²)')
    axes[1].set_title('Affected area against threshold', fontsize=10)
    axes[1].grid(alpha=0.3)
    axes[1].axhline(12, color='#666666', linestyle=':', linewidth=1,
                    label='published flow area, about 12 km²')
    axes[1].legend(fontsize=8, frameon=False)

    path = FIGURES / f'distributions_{index}.png'
    fig.savefig(path, dpi=140)
    plt.close(fig)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', default='ndvi')
    parser.add_argument('--clusters', type=int, default=5)
    args = parser.parse_args()

    FIGURES.mkdir(parents=True, exist_ok=True)
    for builder in (
        lambda: figure_composites(args.index),
        lambda: figure_change(args.index),
        lambda: figure_clusters(args.index, args.clusters),
        lambda: figure_distributions(args.index),
    ):
        path = builder()
        if path is not None:
            print(f'wrote {path}')


if __name__ == '__main__':
    main()
