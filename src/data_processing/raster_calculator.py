from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window

from src.helper.product_metadata import to_reflectance
from src.helper.raster_data import RasterData, RasterState, RasterType


def _ratio(numerator: np.ndarray, denominator: np.ndarray) -> np.ndarray:
    """Divide, yielding NaN rather than a plausible number where undefined.

    A zero denominator means both bands read zero, which is absence of
    measurement, not an index of zero. Returning 0.0 there puts a legitimate
    looking value into the data that then survives every downstream mean,
    median and curve fit. NaN propagates instead, which is the point.
    """
    with np.errstate(divide='ignore', invalid='ignore'):
        result = numerator / denominator
    return np.where(np.isfinite(result), result, np.nan)


class RasterCalculator:
    """Computes spectral indices from Sentinel-2 surface reflectance bands."""

    # Scene classification classes that cannot carry a surface measurement.
    # 0 nodata, 1 saturated or defective, 3 cloud shadow, 8 cloud medium
    # probability, 9 cloud high probability, 10 thin cirrus, 11 snow or ice.
    # Class 2 (cast shadow / dark area) is kept: on a steep volcanic island it
    # is usually genuine terrain shadow, and discarding it would remove the
    # west slopes for much of the year.
    SCL_UNUSABLE = (0, 1, 3, 8, 9, 10, 11)

    NAMED_WINDOWS = {
        'lapalma': Window(393, 340, 3698 - 393, 5148 - 340),
        'lavaflow_lapalma': Window(1209, 2591, 2510 - 1209, 3860 - 2591),
    }

    def __init__(self, band_dir: str, results_folder: str) -> None:
        self.band_dir = band_dir
        self.results_folder = results_folder
        self.borders = Window(0, 0, 0, 0)

    def _selection(
        self,
        tile: str,
        capture_date: str,
        bands: list[str],
        resolution: str = '10m',
        use_window: bool = False,
    ) -> list[RasterData]:
        resolution_dir = f'R{resolution}'
        project_directory = (
            Path(__file__).parents[2] / self.band_dir / tile / capture_date / resolution_dir
        )
        if not project_directory.is_dir():
            raise FileNotFoundError(
                f'No processed bands for {tile} on {capture_date} at '
                f'{project_directory}. Run scripts/download_dataset.py, or check '
                f'the date is one that was acquired.'
            )

        jp2_files = list(project_directory.glob('*.jp2'))
        selected_rasters = []
        for band in bands:
            band_files = [
                RasterData(file, read_with_window=use_window, window=self.borders)
                for file in jp2_files if f'B{band}' in str(file)
            ]
            # Returning short would surface much later as an IndexError inside
            # whichever index function asked for the band.
            if not band_files:
                raise FileNotFoundError(
                    f'Band B{band} at {resolution} is missing for {tile} on '
                    f'{capture_date} in {project_directory}'
                )
            selected_rasters.extend(band_files)
        return selected_rasters

    def _date_dir(self, tile: str, capture_date: str) -> Path:
        return Path(__file__).parents[2] / self.band_dir / tile / capture_date

    def set_borders(self, borders: str | tuple) -> None:
        if isinstance(borders, str):
            if borders not in self.NAMED_WINDOWS:
                raise ValueError(
                    f"Unknown window name '{borders}'. Known: {list(self.NAMED_WINDOWS)}"
                )
            self.borders = self.NAMED_WINDOWS[borders]
        else:
            self.borders = Window(*borders)

    def scene_mask(
        self,
        tile: str,
        capture_date: str,
        use_bounds: bool = False,
        unusable: tuple[int, ...] | None = None,
    ) -> np.ndarray | None:
        """Return a boolean mask of usable pixels, True where measurable.

        Read from the product's own scene classification layer, which is the
        classification the processor already made, rather than inferred from how
        far the index moved between dates. Returns None when no SCL band is
        present, so callers can tell "all usable" from "no classification".

        SCL is a 20 m band, so it is resampled to the 10 m grid with nearest
        neighbour, replicating each class across the 2x2 block it covers. Window
        origins on the two grids coincide exactly, so no offset is introduced.
        """
        unusable = self.SCL_UNUSABLE if unusable is None else unusable
        matches = list((self._date_dir(tile, capture_date) / 'R20m').glob('*_SCL_20m.jp2'))
        if not matches:
            return None

        with rasterio.open(matches[0]) as src:
            if use_bounds:
                window_10m = self.borders
                window_20m = Window(
                    window_10m.col_off / 2, window_10m.row_off / 2,
                    window_10m.width / 2, window_10m.height / 2,
                )
                out_shape = (int(window_10m.height), int(window_10m.width))
            else:
                window_20m = None
                out_shape = (src.height * 2, src.width * 2)
            classes = src.read(
                1, window=window_20m, out_shape=out_shape,
                resampling=Resampling.nearest,
            )

        return ~np.isin(classes, unusable)

    def masked_index(
        self,
        tile: str,
        capture_date: str,
        index: str = 'savi',
        use_bounds: bool = False,
    ) -> np.ndarray:
        """Compute an index with cloud, shadow and snow set to NaN."""
        dispatch = {
            'ndvi': self.calculate_ndvi,
            'savi': self.calculate_savi,
            'ndwi': self.calculate_ndwi,
            'nbr': self.calculate_nbr,
        }
        if index not in dispatch:
            raise ValueError(f"Index '{index}' is not implemented. "
                             f'Choose from: {list(dispatch)}')

        data = dispatch[index](
            tile, capture_date, save_file=False, use_bounds=use_bounds
        ).data.astype('float32')

        mask = self.scene_mask(tile, capture_date, use_bounds=use_bounds)
        if mask is None:
            return data
        return np.where(mask, data, np.nan)

    def calculate_ndvi(
        self,
        tile: str,
        capture_date: str,
        save_file: bool = False,
        use_bounds: bool = False,
    ) -> RasterData:
        bands = self._selection(tile, capture_date, ['04', '08'], use_window=use_bounds)
        date_dir = self._date_dir(tile, capture_date)
        red = to_reflectance(bands[0].data, date_dir)
        nir = to_reflectance(bands[1].data, date_dir)
        ndvi_data = _ratio(nir - red, nir + red)

        ndvi = RasterData(
            data=ndvi_data, meta=bands[0].meta,
            state=RasterState.CALCULATED, rastertype=RasterType.INDEX,
        )
        if save_file:
            ndvi.save(Path(self.results_folder) / f'{tile}_{capture_date}_ndvi.tif')
        return ndvi

    def calculate_savi(
        self,
        tile: str,
        capture_date: str,
        L: float = 0.5,
        save_file: bool = False,
        use_bounds: bool = False,
    ) -> RasterData:
        bands = self._selection(tile, capture_date, ['04', '08'], use_window=use_bounds)
        date_dir = self._date_dir(tile, capture_date)
        red = to_reflectance(bands[0].data, date_dir)
        nir = to_reflectance(bands[1].data, date_dir)
        savi_data = _ratio((nir - red) * (1 + L), nir + red + L)

        savi = RasterData(
            data=savi_data, meta=bands[0].meta,
            state=RasterState.CALCULATED, rastertype=RasterType.INDEX,
        )
        if save_file:
            savi.save(Path(self.results_folder) / f'{tile}_{capture_date}_savi.tif')
        return savi

    def calculate_nbr(
        self,
        tile: str,
        capture_date: str,
        resolution: str = '20m',
        save_file: bool = False,
        use_bounds: bool = False,
    ) -> RasterData:
        # NBR uses 20 m bands (B8A, B12). Halve the 10 m window for selection,
        # then restore the original window.
        original_window = self.borders
        self.borders = Window(
            original_window.col_off / 2,
            original_window.row_off / 2,
            original_window.width / 2,
            original_window.height / 2,
        )
        bands = self._selection(
            tile, capture_date, ['8A', '12'],
            resolution=resolution, use_window=use_bounds,
        )
        self.borders = original_window

        date_dir = self._date_dir(tile, capture_date)
        nir = to_reflectance(bands[0].data, date_dir)
        swir = to_reflectance(bands[1].data, date_dir)
        nbr_data = _ratio(nir - swir, nir + swir)

        nbr = RasterData(
            data=nbr_data, meta=bands[0].meta,
            state=RasterState.CALCULATED, rastertype=RasterType.INDEX,
        )
        if save_file:
            nbr.save(Path(self.results_folder) / f'{tile}_{capture_date}_nbr.tif')
        return nbr

    def calculate_ndwi(
        self,
        tile: str,
        capture_date: str,
        save_file: bool = False,
        use_bounds: bool = False,
    ) -> RasterData:
        bands = self._selection(tile, capture_date, ['03', '08'], use_window=use_bounds)
        date_dir = self._date_dir(tile, capture_date)
        green = to_reflectance(bands[0].data, date_dir)
        nir = to_reflectance(bands[1].data, date_dir)
        ndwi_data = _ratio(green - nir, green + nir)

        ndwi = RasterData(
            data=ndwi_data, meta=bands[0].meta,
            state=RasterState.CALCULATED, rastertype=RasterType.INDEX,
        )
        if save_file:
            ndwi.save(Path(self.results_folder) / f'{tile}_{capture_date}_ndwi.tif')
        return ndwi

    def temporal_comparison(
        self,
        tile: str,
        date1: str,
        date2: str,
        index: str = 'savi',
        save_file: bool = False,
    ) -> RasterData | None:
        dispatch = {
            'savi': self.calculate_savi,
            'ndvi': self.calculate_ndvi,
            'nbr': self.calculate_nbr,
        }
        if index not in dispatch:
            return None
        calc = dispatch[index]
        pre = calc(tile, date1, save_file=False)
        post = calc(tile, date2, save_file=False)
        result = RasterData(
            data=pre.data - post.data, meta=pre.meta,
            state=RasterState.CALCULATED, rastertype=RasterType.INDEX,
        )
        if save_file:
            result.save(Path(self.results_folder) / f'{tile}_{date1}_{date2}_{index}.tif')
        return result
