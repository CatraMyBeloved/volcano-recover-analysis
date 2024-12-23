import numpy as np
import rasterio
import pyvista as pv
from rasterio.warp import reproject
from rasterio.windows import Window
from rasterio.enums import Resampling
from pathlib import Path

from src.helper.coordinate_transform import pixel_to_geographic


def read_dem(source_path, window = None):
    dem_path = Path(__file__).parents[2] / source_path

    with rasterio.open(dem_path) as src:
        if window is not None:
            data = src.read(1, window=window)
        else:
            data = src.read(1)

        meta = src.profile.copy()

        data = data.astype(np.float32)

        data[~np.isfinite(data)] = np.nanmean(data)

    return data, meta

def simple_3d(data, meta):
    transform = meta['transform']

    rows, cols = data.shape

    x = np.arange(0, cols)
    y = np.arange(0, rows)

    x,y = np.meshgrid(x,y)

    grid = pv.StructuredGrid(x,y, data*0.05)

    p = pv.Plotter()

    p.add_mesh(grid,
               scalars= grid.points[:, 2],
               cmap = 'terrain',
               clim = [-10, grid.points[:, 2].max()],
               lighting=True)

    p.add_axes(interactive=True)
    p.add_scalar_bar('Elevation (10m)')
    p.show()


def color_3d(elev_data, elev_meta, color_data, color_meta):
    rows, cols = elev_data.shape

    color_reshaped = reproject(color_data, )

    x = np.arange(0, cols)
    y = np.arange(0, rows)

    x, y = np.meshgrid(x, y)

    grid = pv.StructuredGrid(x, y, data * 0.05)

    p = pv.Plotter()

    p.add_mesh(grid,
               scalars=grid.points[:, 2],
               cmap='magma',
               clim=[-10, grid.points[:, 2].max()],
               lighting=True)

    p.add_axes(interactive=True)
    p.add_scalar_bar('Elevation (10m)')
    p.show()



data, meta = read_dem('data/DEM_merged/merged_30_2.tif', window = Window(
    3473,
    614,
    4804-3623,
    2483-764,
    ))


simple_3d(data, meta)

