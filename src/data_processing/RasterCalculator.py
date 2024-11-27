from pathlib import Path

import numpy as np
import rasterio


class RasterCalculator:
    """
    RasterCalculator: Used to conduct different calculations on raster data captured by sentinel

    Arguments:
        - band_dir: Directory where extracted SAFE folders are stored
        - resolution: Resolution of raster data to examine, standard 10m

    Functions:
        - _selection: Returns path to specific pictures based on tile, capture date and bands.
        - calculate_ndvi: Returns ndvi for selected tile and capture date. Uses B04 and B08 from sentinel 2

    """

    def __init__(self, band_dir, results_folder):
        """Initializes RasterCalculator with standard resolution of 10m and directory for data"""
        self.band_dir = band_dir
        self.results_folder = results_folder

    def _selection(self, tile, capture_date, bands, resolution='10m'):
        """
        Selects files based on criteria and returns their path
        :param tile: Tile to examine
        :param capture_date: Date the picture was captures
        :param bands: which bands to return
        :return: path(s) to selected pictures
        """
        resolution_selection = 'R' + resolution
        project_directory = Path(__file__).parents[2] / self.band_dir / tile / capture_date / resolution_selection
        jp2_files = list(project_directory.glob('*.jp2'))
        selected_files = []
        for band in bands:
            band_files = [file for file in jp2_files if f'B{band}' in str(file)]
            selected_files.extend(band_files)
        return selected_files

    def _save_result(self, result, source_metadata, name, folder=None):
        if folder is None:
            folder = self.results_folder
        else:
            folder = Path(folder)

        project_directory = Path(__file__).parents[2]
        result_directory = project_directory / 'results' / folder

        result_directory.mkdir(parents=True, exist_ok=True)

        metadata = source_metadata.copy()

        metadata.update(
            driver='GTiff',
            dtype='float32',
            count=1,
            nodata=None
        )

        print("Metadata dtype:", metadata['dtype'])
        print("Driver:", metadata['driver'])

        with rasterio.open(result_directory / f"{name}.tif", 'w', **metadata) as dst:
            dst.write(result, 1)

    def calculate_ndvi(self, tile, capture_date, save_file=False):
        """
        Calculates NDVI for selected tile and capture date
        :param tile: Tile to examine
        :param capture_date: Date the data was captured
        :return: numpy array containing NDVI values
        """
        ndvi_band_files = self._selection(tile, capture_date, ['04', '08'])
        with rasterio.open(ndvi_band_files[0]) as red, rasterio.open(ndvi_band_files[1]) as nir:
            source_metadata = red.profile.copy()
            nir_data = nir.read(1)  # reads as numpy array
            red_data = red.read(1)

            nir_scaled = np.clip(nir_data.astype(float) / 10000, 0, 1)
            red_scaled = np.clip(red_data.astype(float) / 10000, 0, 1)

            ndvi = np.where(nir_scaled + red_scaled != 0, (nir_scaled - red_scaled) / (nir_scaled + red_scaled), 0)

        if save_file:
            self._save_result(ndvi, source_metadata, f"{tile}_{capture_date}_ndvi")

        print("NDVI dtype:", ndvi.dtype)
        return ndvi

    def calculate_savi(self, tile, capture_date, L=0.5, save_file=False):
        """
        Calculates SAVI for selected tile and capture date
        :param tile: Tile to examine
        :param capture_date: Date the data was captured
        :param L: L factor
        :return: numpy array containing SAVI values
        """
        savi_band_files = self._selection(tile, capture_date, ['04', '08'])
        with rasterio.open(savi_band_files[0]) as red, rasterio.open(savi_band_files[1]) as nir:
            source_metadata = red.profile.copy()
            nir_data = nir.read(1)  # reads as numpy array
            red_data = red.read(1)

            nir_scaled = np.clip(nir_data.astype(float) / 10000, 0, 1)
            red_scaled = np.clip(red_data.astype(float) / 10000, 0, 1)

            savi = np.where(nir_scaled + red_scaled != 0,
                            ((nir_scaled - red_scaled) / (nir_scaled + red_scaled + L)) * (1 + L), 0)

        if save_file:
            self._save_result(savi, source_metadata, f"{tile}_{capture_date}_savi")

        return savi

    def calculate_nbr(self, tile, capture_date, bands=['8A', '12'], resolution='20m', save_file=False):
        """
        Calculates NBR for selected tile and capture date
        :param tile: Tile to examine
        :param capture_date: Date the data was captured
        :return: numpy array containing NBR values
        """
        nbr_band_files = self._selection(tile, capture_date, bands=bands, resolution=resolution)
        with rasterio.open(nbr_band_files[0]) as nir, rasterio.open(nbr_band_files[1]) as swir:
            source_metadata = swir.profile.copy()
            nir_data = nir.read(1)  # reads as numpy array
            swir_data = swir.read(1)

            nir_scaled = np.clip(nir_data.astype(float) / 10000, 0, 1)
            swir_scaled = np.clip(swir_data.astype(float) / 10000, 0, 1)

            nbr = np.where(nir_scaled + swir_scaled != 0,
                           ((nir_scaled - swir_scaled) / (nir_scaled + swir_scaled)), 0)

        if save_file:
            self._save_result(nbr, source_metadata, f"{tile}_{capture_date}_nbr")

        return nbr

calculator = RasterCalculator('data/processed', 'rasters')
ndvi = calculator.calculate_ndvi('T28RBS', '20211214', save_file=True)
savi = calculator.calculate_savi('T28RBS', '20211214', save_file=True)
nbr = calculator.calculate_nbr('T28RBS', '20211214', save_file=True)
print(nbr)
