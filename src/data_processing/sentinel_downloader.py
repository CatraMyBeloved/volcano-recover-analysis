import os
import zipfile
from pathlib import Path

from cdsetool.credentials import Credentials
from cdsetool.download import download_features
from cdsetool.query import query_features


class SentinelDownloader:
    """Query and download Sentinel-2 products from the Copernicus Data Space Ecosystem.

    Products are fetched as `.zip` archives to `archive_path` and extracted into
    `.SAFE` directories under `raw_path`, where `SentinelProcessor` picks them up.
    """

    COLLECTION = 'Sentinel2'

    def __init__(
        self,
        username: str | None = None,
        password: str | None = None,
        archive_path: str | Path = 'data/archive',
        raw_path: str | Path = 'data/raw',
    ) -> None:
        self.archive_path = Path(archive_path)
        self.raw_path = Path(raw_path)
        self.archive_path.mkdir(parents=True, exist_ok=True)
        self.raw_path.mkdir(parents=True, exist_ok=True)

        username = username or os.environ.get('CDSE_USERNAME')
        password = password or os.environ.get('CDSE_PASSWORD')
        if not username or not password:
            raise ValueError(
                'CDSE credentials missing. Pass username and password to '
                'SentinelDownloader, or set CDSE_USERNAME and CDSE_PASSWORD '
                'environment variables.'
            )
        self.credentials = Credentials(username, password)

    def search(
        self,
        tile: str,
        start_date: str,
        end_date: str,
        max_cloud_cover: int = 30,
        product_type: str = 'S2MSI2A',
    ) -> list[dict]:
        return list(query_features(
            self.COLLECTION,
            {
                'productType': product_type,
                'tileId': tile,
                'contentDateStartGe': start_date,
                'contentDateStartLe': end_date,
                'cloudCover': f'[0,{max_cloud_cover}]',
            },
        ))

    def fetch(
        self,
        tile: str,
        start_date: str,
        end_date: str,
        max_cloud_cover: int = 30,
        product_type: str = 'S2MSI2A',
        concurrency: int = 4,
    ) -> list[str]:
        features = self.search(tile, start_date, end_date, max_cloud_cover, product_type)
        if not features:
            print(f'No products matched tile {tile} between {start_date} and {end_date}')
            return []

        print(f'Found {len(features)} products. Downloading to {self.archive_path}')
        list(download_features(
            features,
            str(self.archive_path),
            {'concurrency': concurrency, 'credentials': self.credentials},
        ))

        return self._extract_archives(features)

    def _extract_archives(self, features: list[dict]) -> list[str]:
        dates: set[str] = set()
        for feature in features:
            name = feature['Name']
            archive_zip = self.archive_path / f'{name}.zip'
            if not archive_zip.exists():
                print(f'Skipping {name}: archive not found at {archive_zip}')
                continue

            safe_dir = self.raw_path / f'{name}.SAFE'
            if not safe_dir.exists():
                with zipfile.ZipFile(archive_zip, 'r') as zf:
                    zf.extractall(self.raw_path)

            # Product name: S2A_MSIL2A_<YYYYMMDD>T<HHMMSS>_N<baseline>_R<orbit>_T<tile>_...
            acquisition_date = name.split('_')[2][:8]
            dates.add(acquisition_date)

        return sorted(dates)
