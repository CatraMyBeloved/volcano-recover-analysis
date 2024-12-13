import numpy as np
import rasterio
import pyvista as pv
from rasterio.windows import Window
from pathlib import Path

def read_dem(source_path):
    dem_path = Path(__file__).parents[2] / source_path
    borders = Window(393, 340, 3698 - 393, 5148 - 340)
    with rasterio.open(dem_path) as src:
        data = src.read(1)
        meta = src.profile.copy()

        # Convert data to float32 and handle NaN values
        data = data.astype(np.float32)
        # Replace any NaN or invalid values with interpolated values
        # For now, let's just use a simple fill with mean value
        data[~np.isfinite(data)] = np.nanmean(data)

    return data, meta

def simple_3d(data, meta):
    transform = meta['transform']

    rows, cols = data.shape

    x = np.arange(0, cols)
    y = np.arange(0, rows)

    x,y = np.meshgrid(x,y)

    grid = pv.StructuredGrid(x,y, data*0.1)

    p = pv.Plotter()

    p.add_mesh(grid,
               scalars= data*0.1,
               cmap = 'magma',
               smooth_shading=True,
               clim = [0, data.max()*0.1],
               lighting=True)

    p.add_axes(interactive=True)
    p.add_scalar_bar('Elevation (m)')
    p.show()

data, meta = read_dem('data/DEM_merged/merged_30.tif')

simple_3d(data, meta)

