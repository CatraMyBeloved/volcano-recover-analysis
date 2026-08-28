"""Check what each downloaded scene actually contains over the study area.

Footprint metadata says where a product claims to hold data; this reads the
pixels and says whether it does. Run after a download and before building any
composite, because a scene that is empty or clouded over the lava flow will
quietly bias a median rather than announce itself.

Reports, per acquisition date:
  valid    fraction of the study window that is not nodata
  usable   fraction that the scene classification calls ground or water rather
           than cloud, cirrus, cloud shadow, snow or saturation

Usage:
    uv run scripts/verify_coverage.py
"""
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window


PROCESSED = Path(__file__).parents[1] / 'data' / 'processed'
TILE = 'T28RBS'

# Pixel windows on the 10 m grid, matching RasterCalculator.NAMED_WINDOWS.
WINDOWS_10M = {
    'island': Window(393, 340, 3305, 4808),
    'lavaflow': Window(1209, 2591, 1301, 1269),
}

# Scene classification classes that cannot carry a vegetation measurement.
# 0 nodata, 1 saturated/defective, 3 cloud shadow, 8 cloud medium probability,
# 9 cloud high probability, 10 thin cirrus, 11 snow or ice.
SCL_UNUSABLE = (0, 1, 3, 8, 9, 10, 11)
# 2 is dark area or topographic shadow. On a steep volcanic island this is
# often genuine terrain shadow rather than contamination, so it is counted
# separately instead of being silently discarded.
SCL_SHADOW = 2


def halve(window: Window) -> Window:
    """Convert a 10 m pixel window to the matching 20 m window."""
    return Window(
        int(window.col_off // 2), int(window.row_off // 2),
        int(window.width // 2), int(window.height // 2),
    )


def band_path(date: str, suffix: str, resolution: str) -> Path | None:
    directory = PROCESSED / TILE / date / f'R{resolution}'
    matches = list(directory.glob(f'*_{suffix}_{resolution}.jp2'))
    return matches[0] if matches else None


def assess(date: str, window_name: str) -> dict | None:
    window_10m = WINDOWS_10M[window_name]

    red = band_path(date, 'B04', '10m')
    if red is None:
        return None
    with rasterio.open(red) as src:
        data = src.read(1, window=window_10m)
    valid = float(np.count_nonzero(data)) / data.size

    result = {'valid': valid, 'usable': None, 'shadow': None}

    scl = band_path(date, 'SCL', '20m')
    if scl is None:
        return result
    with rasterio.open(scl) as src:
        classes = src.read(1, window=halve(window_10m))
    total = classes.size
    unusable = np.isin(classes, SCL_UNUSABLE).sum()
    result['usable'] = float(total - unusable) / total
    result['shadow'] = float((classes == SCL_SHADOW).sum()) / total
    return result


def main() -> None:
    dates = sorted(p.name for p in (PROCESSED / TILE).iterdir() if p.is_dir())
    if not dates:
        raise SystemExit(f'No processed dates under {PROCESSED / TILE}')

    print(f'{len(dates)} scenes under {PROCESSED / TILE}\n')
    header = (f'{"date":10} {"island valid":>13} {"lava valid":>11} '
              f'{"lava usable":>12} {"lava shadow":>12}')
    print(header)
    print('-' * len(header))

    suspect = []
    for date in dates:
        island = assess(date, 'island')
        lava = assess(date, 'lavaflow')
        if island is None or lava is None:
            print(f'{date:10} {"no B04 band":>13}')
            suspect.append((date, 'missing band'))
            continue

        usable = lava['usable']
        shadow = lava['shadow']
        print(f'{date:10} {island["valid"]:12.1%} {lava["valid"]:10.1%} '
              f'{usable:11.1%} {shadow:11.1%}'
              if usable is not None else
              f'{date:10} {island["valid"]:12.1%} {lava["valid"]:10.1%} '
              f'{"no SCL":>11} {"":>11}')

        if lava['valid'] < 0.99:
            suspect.append((date, f'only {lava["valid"]:.1%} valid over the lava flow'))
        elif usable is not None and usable < 0.80:
            suspect.append((date, f'only {usable:.1%} usable over the lava flow'))

    print()
    if suspect:
        print('Scenes contributing little over the lava flow:')
        for date, reason in suspect:
            print(f'  {date}: {reason}')
        print('Per-pixel compositing handles these: a partly clouded scene still\n'
              'contributes its clear pixels, so the count below matters more than\n'
              'any single scene. Do not drop scenes on this table alone.')
    else:
        print('All scenes are fully valid and largely cloud free over the lava flow.')

    print()
    report_observation_depth(dates)


def report_observation_depth(dates: list[str]) -> None:
    """Count clear observations per pixel within each analysis period.

    This is the real test of whether a median composite is supportable. Whole
    scenes can look poor while every pixel still has several clear looks across
    the period, and tile-level cloud cover says nothing about either.
    """
    periods = {
        'baseline 2018+2019': [d for d in dates if d[:4] in ('2018', '2019')],
        'impact 2022': [d for d in dates if d[:4] == '2022'],
        'recovery 2025': [d for d in dates if d[:4] == '2025'],
    }
    lava_20m = halve(WINDOWS_10M['lavaflow'])

    print('Clear observations per pixel over the lava flow')
    for label, period_dates in periods.items():
        if not period_dates:
            continue
        masks = []
        for date in period_dates:
            scl = band_path(date, 'SCL', '20m')
            if scl is None:
                continue
            with rasterio.open(scl) as src:
                classes = src.read(1, window=lava_20m)
            masks.append(~np.isin(classes, SCL_UNUSABLE))
        if not masks:
            continue

        clear = np.sum(masks, axis=0)
        total = clear.size
        blind = 100.0 * np.count_nonzero(clear == 0) / total
        at_least_two = 100.0 * np.count_nonzero(clear >= 2) / total
        print(f'  {label} ({len(masks)} scenes): median {np.median(clear):.0f}, '
              f'{at_least_two:.2f}% of pixels have 2 or more, '
              f'{blind:.2f}% have none')
        if blind > 1.0:
            print('    more than 1% of pixels are never clear; mask and report '
                  'those rather than interpolating them')


if __name__ == '__main__':
    main()
