from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window


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
        self.borders = Window(0, 0, 0, 0)  # xmin, xmax, ymin, ymax

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
        print(jp2_files)
        selected_files = []
        for band in bands:
            band_files = [file for file in jp2_files if f'B{band}' in str(file)]
            selected_files.extend(band_files)
        return selected_files

    def _save_result(self, result, source_metadata, name, folder=None, use_bounds=False):
        if folder is None:
            folder = self.results_folder
        else:
            folder = Path(folder)

        project_directory = Path(__file__).parents[2]
        result_directory = project_directory / 'results' / folder

        result_directory.mkdir(parents=True, exist_ok=True)

        metadata = source_metadata.copy()
        if not use_bounds:
            metadata.update(
                driver='GTiff',
                dtype='float32',
                count=1,
                nodata=None
            )
        else:
            new_transform = rasterio.windows.transform(self.borders, metadata['transform'])
            metadata.update(
                driver='GTiff',
                dtype='float32',
                count=1,
                nodata=None,
                height=self.borders.height,
                width=self.borders.width,
                transform=new_transform
            )



        with rasterio.open(result_directory / f"{name}.tif", 'w', **metadata) as dst:
            dst.write(result, 1)

    def set_borders(self, borders):
        if borders == 'lapalma':
            self.borders = Window(393, 340, 3698-393, 5148-340)
        elif borders == 'lavaflow_lapalma':
            self.borders = Window(1209, 2591, 2510-1209, 3860-2591)
        else:
            self.borders = Window(*borders)

    def calculate_ndvi(self, tile, capture_date, save_file=False, use_bounds=False):
        """
        Calculates NDVI for selected tile and capture date
        :param tile: Tile to examine
        :param capture_date: Date the data was captured
        :return: numpy array containing NDVI values
        """
        ndvi_band_files = self._selection(tile, capture_date, ['04', '08'])
        with rasterio.open(ndvi_band_files[0]) as red, rasterio.open(ndvi_band_files[1]) as nir:
            source_metadata = red.profile.copy()

            if use_bounds:
                nir_data = nir.read(1, window=self.borders)
                red_data = red.read(1, window=self.borders)
            else:
                nir_data = nir.read(1)
                red_data = red.read(1)

            nir_scaled = np.clip(nir_data.astype(float) / 10000, 0, 1)
            red_scaled = np.clip(red_data.astype(float) / 10000, 0, 1)

            ndvi = np.where(nir_scaled + red_scaled != 0, (nir_scaled - red_scaled) / (nir_scaled + red_scaled), 0)

        if save_file:
            if use_bounds:
                self._save_result(ndvi, source_metadata, f"{tile}_{capture_date}_ndvi_crop", use_bounds=use_bounds)
            else:
                self._save_result(ndvi, source_metadata, f"{tile}_{capture_date}_ndvi")

        return ndvi

    def calculate_savi(self, tile, capture_date, L=0.5, save_file=False, use_bounds=False):
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
            if use_bounds:
                nir_data = nir.read(1, window=self.borders)
                red_data = red.read(1, window=self.borders)
            else:
                nir_data = nir.read(1)
                red_data = red.read(1)

            nir_scaled = np.clip(nir_data.astype(float) / 10000, 0, 1)
            red_scaled = np.clip(red_data.astype(float) / 10000, 0, 1)

            savi = np.where(nir_scaled + red_scaled != 0,
                            ((nir_scaled - red_scaled) / (nir_scaled + red_scaled + L)) * (1 + L), 0)

        if save_file:
            if use_bounds:
                self._save_result(savi, source_metadata, f"{tile}_{capture_date}_savi_crop", use_bounds=use_bounds)
            else:
                self._save_result(savi, source_metadata, f"{tile}_{capture_date}_savi")

        return savi

    def calculate_nbr(self, tile, capture_date, bands=None, resolution='20m', save_file=False):
        """
        Calculates NBR for selected tile and capture date
        :param bands: bands to use for calculation
        :param tile: Tile to examine
        :param capture_date: Date the data was captured
        :return: numpy array containing NBR values
        """
        if bands is None:
            bands = ['8A', '12']
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

    def temporal_comparison(self, tile, date1, date2, index='savi', save_file=False):
        if index not in ['savi', 'ndvi', 'nbr']:
            return None

        if index == 'savi':
            pre = self.calculate_savi(tile, date1, save_file=False)
            post = self.calculate_savi(tile, date2, save_file=False)
        elif index == 'nbr':
            pre = self.calculate_nbr(tile, date1, save_file=False)
            post = self.calculate_nbr(tile, date2, save_file=False)
        elif index == 'ndvi':
            pre = self.calculate_ndvi(tile, date1, save_file=False)
            post = self.calculate_ndvi(tile, date2, save_file=False)

        result = post - pre

        if save_file:
            original_file = self._selection(tile, date1, ['02'])
            print(original_file)
            with rasterio.open(original_file[0]) as src:
                metadata = src.profile.copy()

            metadata.update(
                driver='GTiff',
                dtype='float32',
                count=1,
                nodata=None
            )

            self._save_result(result, metadata, f"comp_{tile}_{date1}_{date2}_{index}")
        return post - pre


calculator = RasterCalculator('data/processed', 'rasters')
calculator.set_borders('lavaflow_lapalma')
calculator.calculate_savi('T28RBS', '20220428', save_file=True, use_bounds=True)
