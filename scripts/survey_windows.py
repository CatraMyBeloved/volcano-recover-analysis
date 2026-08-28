"""Survey candidate Sentinel-2 scenes per analysis window without downloading.

Runs metadata queries only, so it costs seconds and no disk. Use it to choose
which scenes are worth fetching before committing to a multi-gigabyte pull.

Windows are season-matched on February to April: post-winter-rain green-up in
the Canaries, so the vegetation signal is strong and comparable across years.
The impact window is the first matching season after the eruption ended
(2021-12-13); the recovery window is the most recent complete same season.

Requires CDSE credentials in CDSE_USERNAME / CDSE_PASSWORD.
"""
from src.data_processing import SentinelDownloader

TILE = 'T28RBS'
MAX_CLOUD_COVER = 30
# What we would actually download per window.
TARGET_SCENES = 5

WINDOWS = [
    ('baseline 2018', '2018-02-01', '2018-04-30'),
    ('baseline 2019', '2019-02-01', '2019-04-30'),
    ('impact 2022', '2022-02-01', '2022-04-30'),
    ('recovery 2025', '2025-02-01', '2025-04-30'),
]


def main() -> None:
    downloader = SentinelDownloader()
    summary = []

    for label, start, end in WINDOWS:
        print(f'\n=== {label}: {start} to {end} ===')
        available = downloader.search(
            tile=TILE, start_date=start, end_date=end,
            max_cloud_cover=MAX_CLOUD_COVER,
        )
        # Select locally from the one query rather than querying twice.
        selected = downloader.select_scenes(available, TARGET_SCENES)
        chosen = {feature['Name'] for feature in selected}

        print(f'{len(available)} scenes under {MAX_CLOUD_COVER}% cloud, '
              f'would take {len(selected)}')

        ranked = sorted(
            available,
            key=lambda f: (downloader.cloud_cover(f) is None,
                           downloader.cloud_cover(f) or 0.0),
        )
        for feature in ranked:
            cover = downloader.cloud_cover(feature)
            shown = f'{cover:5.1f}%' if cover is not None else '   n/a'
            area = downloader.study_area_fraction(feature)
            area_shown = f'{area:6.1%}' if area is not None else '   n/a'
            orbit = feature['Name'].split('_')[4]
            mark = '  ->' if feature['Name'] in chosen else '    '
            print(f'{mark} {downloader.acquisition_date(feature)}  {orbit}  '
                  f'cloud {shown}  island {area_shown}')

        covers = [downloader.cloud_cover(f) for f in selected]
        covers = [c for c in covers if c is not None]
        summary.append((label, len(available), len(selected),
                        max(covers) if covers else None))

    print('\n=== summary ===')
    for label, available, taken, worst in summary:
        worst_shown = f'{worst:.1f}%' if worst is not None else 'n/a'
        print(f'  {label:16} {available:3} available, take {taken}, '
              f'worst selected cloud {worst_shown}')
    print('\nNothing was downloaded. Arrows mark the scenes the download would take.')


if __name__ == '__main__':
    main()
