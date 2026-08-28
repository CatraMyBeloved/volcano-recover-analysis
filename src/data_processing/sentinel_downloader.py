import logging
import os
import zipfile
from pathlib import Path

from cdsetool.credentials import Credentials
from cdsetool.query import query_features
from shapely.geometry import box, shape

# cdsetool.download is deliberately unused. Its _download_raw retries ten times
# with a 60 s sleep between attempts, logs only to a logger that defaults to
# silent, sets no request timeout, and its redirect handling hangs against the
# CDSE download host. A failure there is indistinguishable from a hang. See
# SentinelDownloader.download for the replacement.

logger = logging.getLogger(__name__)


class SentinelDownloader:
    """Query and download Sentinel-2 products from the Copernicus Data Space Ecosystem.

    Products are fetched as `.zip` archives to `archive_path` and extracted into
    `.SAFE` directories under `raw_path`, where `SentinelProcessor` picks them up.
    """

    # cdsetool queries the OData API, whose collection names are upper case and
    # hyphenated. The OpenSearch spelling ('Sentinel2') is rejected with
    # HTTP 400 "Invalid value".
    COLLECTION = 'SENTINEL-2'

    # cdsetool defaults to 10 attempts with a 60 s sleep between each and a
    # NoopLogger, so a rejected query looks like a ten-minute hang. Fail fast
    # and route its warnings somewhere visible instead.
    QUERY_OPTIONS = {
        'max_attempts': 3,
        'logger': logger,
        'expand_attributes': True,
    }

    # La Palma, WGS84. Tile T28RBS is far larger than the island, and only some
    # orbits image the part of the tile the island sits in, so covering the tile
    # is not the same as covering the study area.
    STUDY_AREA = (-18.00, 28.44, -17.71, 28.87)

    ODATA = 'https://catalogue.dataspace.copernicus.eu/odata/v1'
    # (connect, read). A read timeout matters most: without one a stalled
    # transfer blocks forever.
    TIMEOUT = (30, 120)
    MAX_REDIRECTS = 6

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

    @staticmethod
    def _normalise_tile(tile: str) -> str:
        """Strip the leading 'T' from a tile ID.

        The catalogue stores tileId as '28RBS'. Passing the 'T28RBS' form used
        in product names and in data_inventory.md matches nothing at all, and
        the query returns zero results rather than an error.
        """
        return tile[1:] if tile.upper().startswith('T') else tile

    @staticmethod
    def _day_bounds(start_date: str, end_date: str) -> tuple[str, str]:
        """Expand bare YYYY-MM-DD filters to an inclusive instant range.

        A bare end date is read as midnight, which silently drops every
        acquisition on the end date itself.
        """
        start = start_date if 'T' in start_date else f'{start_date}T00:00:00.000Z'
        end = end_date if 'T' in end_date else f'{end_date}T23:59:59.999Z'
        return start, end

    @staticmethod
    def cloud_cover(feature: dict) -> float | None:
        """Read the cloudCover attribute off an expanded feature."""
        for attribute in feature.get('Attributes') or ():
            if attribute.get('Name') == 'cloudCover':
                try:
                    return float(attribute['Value'])
                except (KeyError, TypeError, ValueError):
                    return None
        return None

    def study_area_fraction(self, feature: dict) -> float | None:
        """Fraction of the study area inside this product's data footprint.

        Returns None when the product carries no footprint.
        """
        footprint = feature.get('GeoFootprint')
        if not footprint:
            return None
        area = box(*self.STUDY_AREA)
        try:
            geometry = shape(footprint)
        except (AttributeError, KeyError, TypeError, ValueError):
            return None
        return geometry.intersection(area).area / area.area

    def _drop_uncovered(
        self, features: list[dict], min_fraction: float
    ) -> list[dict]:
        """Discard products whose footprint misses the study area.

        Tile T28RBS spans far more ground than La Palma, and the two relative
        orbits that reach it differ completely: one images the island in full,
        the other clips a corner of the tile well away from it and covers under
        a tenth of the island. Both yield large, valid products. Worse, because
        cloudCover is assessed only over valid pixels, a granule that barely
        touches the island reports near-zero cloud and therefore wins any
        ranking by clearness. Footprint has to be checked before cloud.
        """
        kept, dropped = [], []
        for feature in features:
            fraction = self.study_area_fraction(feature)
            # Keep products with no footprint rather than guess; the size filter
            # and the post-download pixel check still apply to them.
            if fraction is None or fraction >= min_fraction:
                kept.append(feature)
            else:
                dropped.append((feature, fraction))

        if dropped:
            print(f'  {len(dropped)} of {len(features)} products miss the study '
                  f'area (best {max(f for _, f in dropped):.1%} coverage), skipping')

        return kept

    def _drop_undersized(
        self, features: list[dict], min_fraction: float
    ) -> list[dict]:
        """Discard edge-of-swath granules that hold almost no imagery.

        This catches a different failure from `_drop_uncovered`: a product whose
        footprint does claim the study area but which is nonetheless almost all
        nodata. Its giveaway is size, since nodata compresses to nothing, so an
        empty granule runs tens of megabytes against several hundred for a full
        one. Both filters are needed; each was added for an observed case.

        The threshold is relative to the median of the matched set rather than
        an absolute figure, so it travels to other tiles and product types. It
        is set low deliberately: a truly empty granule runs a few percent of
        the median, whereas a merely partial one runs closer to half, and this
        heuristic is not sharp enough to judge the latter. Coverage of the study
        area is verified against the pixels after download, not guessed here.
        """
        sizes = [f.get('ContentLength') or 0 for f in features]
        usable = sorted(size for size in sizes if size > 0)
        if not usable:
            return features

        median = usable[len(usable) // 2]
        threshold = median * min_fraction
        kept, dropped = [], []
        for feature in features:
            if (feature.get('ContentLength') or 0) >= threshold:
                kept.append(feature)
            else:
                dropped.append(feature)

        for feature in dropped:
            size_mb = (feature.get('ContentLength') or 0) / 1e6
            print(f'  skipping {self.acquisition_date(feature)}: {size_mb:.1f} MB '
                  f'against a {median / 1e6:.0f} MB median, treating as empty')

        return kept

    def select_scenes(self, features: list[dict], max_scenes: int) -> list[dict]:
        """Pick the clearest `max_scenes`, at most one per acquisition date."""
        ranked = sorted(
            features,
            key=lambda f: (self.cloud_cover(f) is None, self.cloud_cover(f) or 0.0),
        )

        # One scene per acquisition date. The catalogue holds reprocessed
        # duplicates of the same acquisition under different processing
        # baselines, and neighbouring orbits can both cover the tile; either
        # way a second copy of the same day adds no information to a composite.
        seen: set[str] = set()
        unique = []
        for feature in ranked:
            date = self.acquisition_date(feature)
            if date in seen:
                continue
            seen.add(date)
            unique.append(feature)

        return unique[:max_scenes]

    def search(
        self,
        tile: str,
        start_date: str,
        end_date: str,
        max_cloud_cover: int = 30,
        product_type: str = 'S2MSI2A',
        max_scenes: int | None = None,
        min_size_fraction: float = 0.25,
        min_coverage: float = 0.99,
    ) -> list[dict]:
        """Return matching products, optionally the `max_scenes` clearest ones.

        Products that miss the study area or hold no imagery are always
        discarded, whether or not a cap applies, and before any ranking by
        cloud cover. See `_drop_uncovered` and `_drop_undersized`.
        """
        start, end = self._day_bounds(start_date, end_date)
        features = list(query_features(
            self.COLLECTION,
            {
                'productType': product_type,
                'tileId': self._normalise_tile(tile),
                'contentDateStartGe': start,
                'contentDateStartLe': end,
                'cloudCover': f'[0,{max_cloud_cover}]',
            },
            options=self.QUERY_OPTIONS,
        ))
        features = self._drop_uncovered(features, min_coverage)
        features = self._drop_undersized(features, min_size_fraction)
        if max_scenes is None:
            return features
        return self.select_scenes(features, max_scenes)

    @staticmethod
    def acquisition_date(feature: dict) -> str:
        """Extract the YYYYMMDD acquisition date from a product name."""
        parts = feature.get('Name', '').split('_')
        return parts[2][:8] if len(parts) > 2 else ''

    def _open_product_stream(self, product_id: str):
        """Open a streaming response for a product, following redirects by hand.

        The catalogue answers with a 301 to download.dataspace.copernicus.eu,
        and requests drops the Authorization header on a cross-host redirect,
        which the download host answers with 401 DAT-ZIP-604 "Token not found".
        Following the chain manually keeps the bearer token attached.
        """
        session = self.credentials.get_session()
        url = f'{self.ODATA}/Products({product_id})/$value'

        for _ in range(self.MAX_REDIRECTS):
            response = session.get(
                url, allow_redirects=False, stream=True, timeout=self.TIMEOUT
            )
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get('Location')
                response.close()
                if not location:
                    raise RuntimeError('redirect without a Location header')
                url = location
                continue
            return response

        raise RuntimeError(f'more than {self.MAX_REDIRECTS} redirects')

    def download(self, feature: dict) -> Path | None:
        """Download one product archive. Returns its path, or None on failure.

        Writes to a temporary name and renames on completion, so an interrupted
        download can never be mistaken for a finished one.
        """
        name = feature['Name']
        target = self.archive_path / f'{name}.zip'
        expected = int(feature.get('ContentLength') or 0)

        if target.exists() and (not expected or target.stat().st_size == expected):
            print(f'  have    {name}', flush=True)
            return target

        partial = target.with_suffix('.zip.partial')
        try:
            with self._open_product_stream(feature['Id']) as response:
                if response.status_code != 200:
                    print(f'  HTTP {response.status_code} for {name}: '
                          f'{response.text[:200]}', flush=True)
                    return None

                size = int(response.headers.get('Content-Length') or expected or 0)
                written = 0
                with open(partial, 'wb') as handle:
                    for chunk in response.iter_content(chunk_size=4 << 20):
                        handle.write(chunk)
                        written += len(chunk)

            if size and written != size:
                print(f'  truncated {name}: {written} of {size} bytes', flush=True)
                partial.unlink(missing_ok=True)
                return None

            partial.replace(target)
            print(f'  got     {name}  ({written / 1e6:.0f} MB)', flush=True)
            return target
        except Exception as exc:
            print(f'  failed  {name}: {type(exc).__name__}: {exc}', flush=True)
            partial.unlink(missing_ok=True)
            return None

    def fetch(
        self,
        tile: str,
        start_date: str,
        end_date: str,
        max_cloud_cover: int = 30,
        product_type: str = 'S2MSI2A',
        max_scenes: int | None = None,
    ) -> list[str]:
        features = self.search(
            tile, start_date, end_date, max_cloud_cover, product_type, max_scenes
        )
        if not features:
            print(f'No products matched tile {tile} between {start_date} and {end_date}')
            return []

        print(f'Found {len(features)} products. Downloading to {self.archive_path}')
        downloaded = []
        for feature in features:
            cover = self.cloud_cover(feature)
            shown = f'{cover:.1f}%' if cover is not None else 'n/a'
            print(f'  cloud {shown:>6}  {feature["Name"]}', flush=True)
            if self.download(feature) is not None:
                downloaded.append(feature)

        if len(downloaded) < len(features):
            print(f'  {len(features) - len(downloaded)} of {len(features)} failed')

        return self._extract_archives(downloaded)

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
