"""Run the post-eruption vegetation recovery analysis for a Sentinel-2 tile.

Dates are discovered from `data/processed/<tile>/`. Run
`scripts/download_dataset.py` first to populate that directory.
"""
import argparse
from pathlib import Path

from src.data_processing import Timeseries

PROCESSED_DIR = Path('data/processed')


def discover_dates(tile: str, start: str | None, end: str | None) -> list[str]:
    tile_dir = PROCESSED_DIR / tile
    if not tile_dir.is_dir():
        raise SystemExit(
            f'No processed data for tile {tile} at {tile_dir}. '
            f'Run scripts/download_dataset.py to acquire it.'
        )
    available = sorted(d.name for d in tile_dir.iterdir() if d.is_dir())
    if start:
        available = [d for d in available if d >= start.replace('-', '')]
    if end:
        available = [d for d in available if d <= end.replace('-', '')]
    if not available:
        raise SystemExit(f'No dates available for tile {tile} in the requested range.')
    return available


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('--tile', default='T28RBS',
                        help='Sentinel-2 tile ID (default: T28RBS)')
    parser.add_argument('--bounds', default='lapalma',
                        help='Named pixel window: lapalma, lavaflow_lapalma '
                             '(default: lapalma)')
    parser.add_argument('--index', default='savi', choices=['ndvi', 'savi', 'ndwi'],
                        help='Spectral index to compute (default: savi)')
    parser.add_argument('--start', help='Inclusive start date, YYYY-MM-DD')
    parser.add_argument('--end', help='Inclusive end date, YYYY-MM-DD')
    parser.add_argument('--clusters', type=int, default=5,
                        help='K-means cluster count, 0 to skip (default: 5)')
    parser.add_argument('--slopes', action='store_true',
                        help='Also compute and save a per-pixel slope raster')
    parser.add_argument('--list', action='store_true',
                        help='List available dates and exit')
    args = parser.parse_args()

    dates = discover_dates(args.tile, args.start, args.end)
    print(f'{len(dates)} dates available for tile {args.tile}: '
          f'{dates[0]} to {dates[-1]}')
    if args.list:
        for d in dates:
            print(f'  {d}')
        return

    analysis = Timeseries(tile=args.tile, dates=dates, bounds=args.bounds)
    analysis.create_timeseries_matrix(args.index)

    if args.clusters > 0:
        analysis.create_clusters_matrix(n_clusters=args.clusters, save_raster=True)
        print(f'Cluster raster ({args.clusters} clusters) saved to results/analysis_results/')

    if args.slopes:
        analysis.calculate_slopes(save_raster=True)
        print('Slope raster saved to results/analysis_results/')


if __name__ == '__main__':
    main()
