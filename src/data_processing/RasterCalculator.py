import geopandas as gpd
import rasterio
import numpy as np
from pathlib import Path

class RasterCalculator:
    def __init__(self, band_dir, resolution = '10m'):
        self.band_dir = band_dir
        self.resolution = resolution

    def _selection(self, tile, capture_date, bands):
        resolution_selection = 'R' + self.resolution
        file_dir = Path(__file__).parents[2] / self.band_dir / tile / capture_date / resolution_selection
        jp2_files = list(file_dir.glob('*.jp2'))

        selected_files = []
        for band in bands:
            band_files = [file for file in jp2_files if f'B{band}' in str(file)]
            selected_files.extend(band_files)
        return selected_files

    def calculate_ndvi(self, tile, capture_date):
        ndvi_band_files = self._selection(tile, capture_date, ['04', '08'])
        with rasterio.open(ndvi_band_files[0]) as red, rasterio.open(ndvi_band_files[1]) as nir:
            nir_data = nir.read(1)  # reads as numpy array
            red_data = red.read(1)

            nir_scaled = np.clip(nir_data.astype(float)/10000, 0, 1)
            red_scaled = np.clip(red_data.astype(float)/10000, 0, 1)

            ndvi = np.where(nir_scaled + red_scaled !=0, (nir_scaled - red_scaled) / (nir_scaled + red_scaled), 0)
            return ndvi


calculator = RasterCalculator('data/processed')
selection = calculator.calculate_ndvi('T28RBS', '20210722')
