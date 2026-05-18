"""Render a SAVI raster as a 3D surface draped over the La Palma DEM."""
from rasterio.windows import Window

from src.visualization.visualizer_3d import color_3d, read_dem

DEM_PATH = 'data/DEM_merged/merged_30_2.tif'
DEM_WINDOW = Window(3481, 642, 4663 - 3481, 2362 - 642)
SAVI_PATH = 'results/rasters/T28RBS_20180807_savi.tif'

elev_data, elev_meta = read_dem(DEM_PATH, window=DEM_WINDOW)
color_data, color_meta = read_dem(SAVI_PATH)
color_3d(elev_data, elev_meta, color_data, color_meta, scalar_name='savi')
