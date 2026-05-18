from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

from src.helper.raster_data import RasterData, RasterState, RasterType


class RasterCalculator:
    """Computes spectral indices from Sentinel-2 surface reflectance bands."""

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
        jp2_files = list(project_directory.glob('*.jp2'))
        selected_rasters = []
        for band in bands:
            band_files = [
                RasterData(file, read_with_window=use_window, window=self.borders)
                for file in jp2_files if f'B{band}' in str(file)
            ]
            selected_rasters.extend(band_files)
        return selected_rasters

    def set_borders(self, borders: str | tuple) -> None:
        if isinstance(borders, str):
            if borders not in self.NAMED_WINDOWS:
                raise ValueError(
                    f"Unknown window name '{borders}'. Known: {list(self.NAMED_WINDOWS)}"
                )
            self.borders = self.NAMED_WINDOWS[borders]
        else:
            self.borders = Window(*borders)

    def calculate_ndvi(
        self,
        tile: str,
        capture_date: str,
        save_file: bool = False,
        use_bounds: bool = False,
    ) -> RasterData:
        bands = self._selection(tile, capture_date, ['04', '08'], use_window=use_bounds)
        red = np.clip(bands[0].data / 10000, 0, 1)
        nir = np.clip(bands[1].data / 10000, 0, 1)
        ndvi_data = np.where(nir + red != 0, (nir - red) / (nir + red), 0)

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
        red = np.clip(bands[0].data / 10000, 0, 1)
        nir = np.clip(bands[1].data / 10000, 0, 1)
        savi_data = np.where(
            nir + red != 0,
            ((nir - red) / (nir + red + L)) * (1 + L),
            0,
        )

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

        nir = np.clip(bands[0].data / 10000, 0, 1)
        swir = np.clip(bands[1].data / 10000, 0, 1)
        nbr_data = np.where(nir + swir != 0, (nir - swir) / (nir + swir), 0)

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
        green = np.clip(bands[0].data / 10000, 0, 1)
        nir = np.clip(bands[1].data / 10000, 0, 1)
        ndwi_data = np.where(green + nir != 0, (green - nir) / (nir + green), -0.2)

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
