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

    #downsample color data to match elevation data

    print(color_data)
    color_data = color_data.reshape((1, *color_data.shape))
    output = np.zeros((1, rows, cols), dtype=color_data.dtype)
    with rasterio.io.MemoryFile() as memfile:
        # Create a temporary raster in memory with the color data
        with memfile.open(
                driver='GTiff',
                height=color_data.shape[1],
                width=color_data.shape[2],
                count=1,
                dtype=color_data.dtype,
                crs=color_meta['crs'],
                transform=color_meta['transform']
        ) as dataset:
            dataset.write(color_data)

            # Read it back at our target resolution
            output = dataset.read(
                1,  # first band
                out_shape=(rows, cols),
                resampling=Resampling.average
            )

    output_2d = output[0]
    print(output)
    x = np.arange(0, cols)
    y = np.arange(0, rows)

    x, y = np.meshgrid(x, y)

    grid = pv.StructuredGrid(x, y, elev_data * 0.05, )

    grid.point_data['savi'] = output.flatten(order = 'F')
    print(grid.point_data['savi'])

    p = pv.Plotter()

    p.add_mesh(grid,
               scalars='savi',
               cmap='YlGn',
               clim=[0,1],
               lighting=True)

    p.add_axes(interactive=True)
    p.show()



elev_data, elev_meta = read_dem('data/DEM_merged/merged_30_2.tif', window =
Window(
    3481,
    642,
    4663-3481,
    2362-642,
    ))

color_data, color_meta = read_dem('results/rasters/T28RBS_20180807_savi.tif')

color_3d(elev_data, elev_meta, color_data, color_meta)

