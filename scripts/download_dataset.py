"""End-to-end data acquisition for the La Palma study area.

Downloads Sentinel-2 Level-2A products for tile T28RBS covering pre-eruption
baseline (2018-2019), the Cumbre Vieja eruption (2021), and the first recovery
year (2022). Extracts each archive into data/raw/ and runs the band extraction
into data/processed/.

Requires CDSE credentials in environment variables CDSE_USERNAME / CDSE_PASSWORD.
Register at dataspace.copernicus.eu.
"""
from src.data_processing import SentinelDownloader, SentinelProcessor

TILE = 'T28RBS'
DATE_RANGES = [
    ('2018-01-01', '2018-12-31'),
    ('2019-01-01', '2019-12-31'),
    ('2021-09-01', '2021-12-31'),
    ('2022-01-01', '2022-12-31'),
]
MAX_CLOUD_COVER = 30

downloader = SentinelDownloader()

all_dates: list[str] = []
for start, end in DATE_RANGES:
    print(f'\n=== {start} to {end} ===')
    dates = downloader.fetch(
        tile=TILE,
        start_date=start,
        end_date=end,
        max_cloud_cover=MAX_CLOUD_COVER,
    )
    all_dates.extend(dates)
    print(f'Acquired {len(dates)} dates: {dates}')

print(f'\nTotal: {len(all_dates)} acquisitions across {len(DATE_RANGES)} windows')
print('\nExtracting bands from SAFE archives...')
SentinelProcessor().process_all()
print('Done. Run main.py or build a Timeseries with the dates above.')
