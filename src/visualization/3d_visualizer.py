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

        data = data.astype(np.float32)
        data[~np.isfinite(data)] = np.nanmean(data)

    return data, meta

def simple_3d(data, meta):
    transform = meta['transform']


    transform = meta['transform']
    rows, cols = data.shape

    x = np.arange(0, cols)
    y = np.arange(0, rows)

    x, y = np.meshgrid(x, y)
    z = data*0.1
    grid = pv.StructuredGrid(x,y, z)

    p = pv.Plotter()

    p.add_mesh(grid,
               scalars= z.flatten(),
               clim=[-3,3000],
               smooth_shading=False,
               lighting=True)

    p.add_axes(interactive=True)
    p.show()

data, meta = read_dem('data/DEM_merged/merged_30.tif')


simple_3d(data, meta)