from pathlib import Path
from src.helper import *
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

    def _selection(self, tile, capture_date, bands, resolution='10m',
                   use_window = False):
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
        selected_rasters = []
        for band in bands:

            band_files = [RasterData(file, read_with_window = use_window,
                                     window = self.borders)
                          for file in jp2_files if f'B{band}' in str(file)]
            selected_rasters.extend(band_files)
        print(jp2_files)
        return selected_rasters


    def set_borders(self, borders):
        if borders == 'lapalma':
            self.borders = Window(393, 340, 3698-393, 5148-340)
        elif borders == 'lavaflow_lapalma':
            self.borders = Window(1209, 2591, 2510-1209, 3860-2591)
        else:
            self.borders = Window(*borders)

    def calculate_ndvi(self, tile, capture_date, save_file=False,
                       use_bounds=False):
        """
        Calculates NDVI for selected tile and capture date
        :param tile: Tile to examine
        :param capture_date: Date the data was captured
        :return: numpy array containing NDVI values
        """
        ndvi_band_data = self._selection(tile, capture_date, ['04', '08'], use_window = use_bounds)
        red = np.clip(ndvi_band_data[0].data/10000, 0, 1)
        nir = np.clip(ndvi_band_data[1].data/10000, 0, 1)


        ndvi_data = np.where(nir + red != 0, (nir - red) / (nir + red), 0)

        ndvi = RasterData(data = ndvi_data, meta = ndvi_band_data[0].meta,
                          state = RasterState.CALCULATED, rastertype =
                          RasterType.INDEX)

        if save_file:
            ndvi.save(self.results_folder / f'{tile}_{capture_date}_ndvi.tif')
        return ndvi

    def calculate_savi(self, tile, capture_date, L=0.5, save_file=False, use_bounds=False):
        """
        Calculates SAVI for selected tile and capture date
        :param tile: Tile to examine
        :param capture_date: Date the data was captured
        :param L: L factor
        :return: numpy array containing SAVI values
        """
        savi_band_data = self._selection(tile, capture_date, ['04', '08'],
                                         use_window=use_bounds)

        red = np.clip(savi_band_data[0].data / 10000, 0, 1)
        nir = np.clip(savi_band_data[1].data / 10000, 0, 1)
        savi_data = np.where(nir + red != 0, ((nir - red) / (nir + red + L))
                             * (1 + L), 0)


        savi = RasterData(data = savi_data, meta = savi_band_data[0].meta,
                          state = RasterState.CALCULATED, rastertype=
                          RasterType.INDEX)


        if save_file:
            savi.save(Path(self.results_folder) / f'{tile}_{capture_date}_savi.tif')
        return savi

    def calculate_nbr(self, tile, capture_date, resolution='20m',
                      save_file=False, use_bounds=False):
        """
        Calculates NBR for selected tile and capture date
        :param bands: bands to use for calculation
        :param tile: Tile to examine
        :param capture_date: Date the data was captured
        :return: numpy array containing NBR values
        """
        bands = ['8A', '12']
        temp_bounds = [self.borders.col_off / 2, self.borders.row_off / 2,
                       self.borders.width / 2, self.borders.height / 2]
        new_bounds = Window(*temp_bounds)
        orig_bounds = self.borders
        self.borders = new_bounds

        nbr_band_data = self._selection(tile, capture_date, bands=bands,
                                     resolution=resolution,
                                        use_window=use_bounds)
        self.borders = orig_bounds
        nir = np.clip(nbr_band_data[0].data / 10000, 0, 1)
        swir = np.clip(nbr_band_data[1].data / 10000, 0, 1)
        nbr_data = np.where(nir + swir != 0, ((nir - swir) / (nir + swir)), 0)

        nbr = RasterData(data = nbr_data, meta = nbr_band_data[0].meta,
                         state = RasterState.CALCULATED, rastertype= RasterType.INDEX)


        if save_file:
            nbr.save(Path(self.results_folder) / f'{tile}_{capture_date}_nbr.tif')
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
        else:
            print('Please select a valid index')
            return None
        result = RasterData(data = pre - post, meta = pre.meta, state =
        RasterState.CALCULATED, rastertype= RasterType.INDEX)
        if save_file:
            result.save(self.results_folder / f'{tile}_{date1}_{date2}_{index}.png')
        return result

    def calculate_ndwi(self, tile, capture_date, save_file = False,
                   use_bounds=False):
        water_band_data = self._selection(tile, capture_date, ['03', '08'])

        green = np.clip(water_band_data[0].data / 10000, 0, 1)
        nir = np.clip(water_band_data[1].data / 10000, 0, 1)
        ndwi_data = np.where(green + nir != 0, ((green - nir) / (nir + green)), -0.2)

        ndwi = RasterData(data = ndwi_data, meta = water_band_data[0].meta,
                          state = RasterState.CALCULATED, rastertype= RasterType.INDEX)
        if save_file:
            ndwi.save(Path(self.results_folder) / f'{tile}_{capture_date}_ndwi.tif')

        return ndwi



