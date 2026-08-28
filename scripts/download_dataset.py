"""End-to-end data acquisition for the La Palma study area.

Downloads Sentinel-2 Level-2A products for tile T28RBS, extracts each archive
into data/raw/, and runs band extraction into data/processed/.

Windows are season-matched on February to April, which is post-winter-rain
green-up in the Canaries, so vegetation signal is strong and comparable across
years rather than confounded by season. Two baseline years are pulled so the
pre-eruption composite rests on more than one season. The impact window is the
first matching season after the eruption ended (2021-12-13). The recovery window
is the most recent complete same season, fetched now so phase two needs no
second pull.

Only the clearest MAX_SCENES per window are taken, one per acquisition date.
Run scripts/survey_windows.py first to see the selection without downloading.

Requires CDSE credentials in environment variables CDSE_USERNAME / CDSE_PASSWORD.
Register at dataspace.copernicus.eu.
"""
from src.data_processing import SentinelDownloader, SentinelProcessor

TILE = 'T28RBS'
DATE_RANGES = [
    ('baseline 2018', '2018-02-01', '2018-04-30'),
    ('baseline 2019', '2019-02-01', '2019-04-30'),
    ('impact 2022', '2022-02-01', '2022-04-30'),
    ('recovery 2025', '2025-02-01', '2025-04-30'),
]
MAX_CLOUD_COVER = 30
MAX_SCENES = 5

downloader = SentinelDownloader()

all_dates: list[str] = []
for label, start, end in DATE_RANGES:
    print(f'\n=== {label}: {start} to {end} ===', flush=True)
    dates = downloader.fetch(
        tile=TILE,
        start_date=start,
        end_date=end,
        max_cloud_cover=MAX_CLOUD_COVER,
        max_scenes=MAX_SCENES,
    )
    all_dates.extend(dates)
    print(f'Acquired {len(dates)} dates: {dates}', flush=True)

print(f'\nTotal: {len(all_dates)} acquisitions across {len(DATE_RANGES)} windows')
print('\nExtracting bands from SAFE archives...', flush=True)
SentinelProcessor().process_all()
print('Done. Run main.py or build a Timeseries with the dates above.')
