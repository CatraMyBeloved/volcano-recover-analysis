"""Build masked median composites for the analysis periods.

Three periods, all season-matched on February to April so vegetation is
comparable rather than confounded by season:

    baseline   pre-eruption, 2018 and 2019 pooled
    impact     first matching season after the eruption ended 2021-12-13
    recovery   most recent complete same season

Writes, per period, a median index raster and the count of clear observations
behind each pixel. Cloud on any single date is common here but moves between
dates, so compositing recovers pixels that no single scene provides.

Usage:
    uv run scripts/build_composites.py [--index ndvi] [--bounds lavaflow_lapalma]
"""
import argparse
import json
from pathlib import Path


from src.data_processing.compositing import Compositor

PROCESSED = Path(__file__).parents[1] / 'data' / 'processed'

PERIODS = {
    'baseline': ('2018', '2019'),
    'impact': ('2022',),
    'recovery': ('2025',),
}


def dates_for(tile: str, years: tuple[str, ...]) -> list[str]:
    available = sorted(p.name for p in (PROCESSED / tile).iterdir() if p.is_dir())
    return [d for d in available if d[:4] in years]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tile', default='T28RBS')
    parser.add_argument('--index', default='ndvi', choices=['ndvi', 'savi', 'ndwi', 'nbr'])
    parser.add_argument('--bounds', default='lavaflow_lapalma')
    parser.add_argument('--min-observations', type=int, default=2,
                        help='pixels with fewer clear looks are left as gaps '
                             '(default: 2)')
    parser.add_argument('--clusters', type=int, default=0,
                        help='also cluster pixels by their per-period composite '
                             'values, 0 to skip (default: 0)')
    args = parser.parse_args()

    compositor = Compositor(tile=args.tile, bounds=args.bounds)
    summaries = []

    for label, years in PERIODS.items():
        dates = dates_for(args.tile, years)
        if not dates:
            print(f'{label}: no dates for {years}, skipping')
            continue

        print(f'\n=== {label}: {len(dates)} scenes ===')
        print(f'  {", ".join(dates)}')
        compositor.composite_raster(
            dates, index=args.index,
            min_observations=args.min_observations,
            label=label, save=True,
        )
        summary = compositor.summarise(
            dates, args.index, label,
            min_observations=args.min_observations,
        )
        summaries.append(summary)
        print(f'  observations per pixel: median '
              f'{summary["median_observations"]:.0f}, min '
              f'{summary["min_observations"]}')
        print(f'  composited: {summary["pixels_composited"]:.2f}% of pixels')
        print(f'  median {args.index}: {summary["median_value"]:+.3f}')

    if args.clusters > 0:
        print(f'\n=== clustering into {args.clusters} recovery patterns ===')
        period_dates = {
            label: dates_for(args.tile, years)
            for label, years in PERIODS.items()
        }
        period_dates = {k: v for k, v in period_dates.items() if v}
        _, centres = compositor.cluster_periods(
            period_dates, index=args.index, n_clusters=args.clusters,
            min_observations=args.min_observations, save=True,
        )
        header = '  '.join(f'{label:>9}' for label in period_dates)
        print(f'  cluster  {header}')
        for number, centre in enumerate(centres):
            values = '  '.join(f'{value:+9.3f}' for value in centre)
            print(f'  {number:>7}  {values}')

    record = Path('results/analysis_results') / f'composites_{args.index}_{args.bounds}.json'
    record.parent.mkdir(parents=True, exist_ok=True)
    record.write_text(json.dumps(summaries, indent=2), encoding='utf-8')
    print(f'\nProvenance written to {record}')


if __name__ == '__main__':
    main()
