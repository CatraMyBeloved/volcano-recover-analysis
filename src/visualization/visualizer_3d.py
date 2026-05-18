from pathlib import Path

import numpy as np
import pyvista as pv
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import Window


def read_dem(source_path: str | Path, window: Window | None = None) -> tuple[np.ndarray, dict]:
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


def simple_3d(data: np.ndarray, meta: dict, elevation_scale: float = 0.05) -> None:
    rows, cols = data.shape
    x, y = np.meshgrid(np.arange(cols), np.arange(rows))
    grid = pv.StructuredGrid(x, y, data * elevation_scale)

    plotter = pv.Plotter()
    plotter.add_mesh(
        grid,
        scalars=grid.points[:, 2],
        cmap='terrain',
        clim=[-10, grid.points[:, 2].max()],
        lighting=True,
    )
    plotter.add_axes(interactive=True)
    plotter.add_scalar_bar('Elevation (10m)')
    plotter.show()


def color_3d(
    elev_data: np.ndarray,
    elev_meta: dict,
    color_data: np.ndarray,
    color_meta: dict,
    elevation_scale: float = 0.05,
    scalar_name: str = 'index',
) -> None:
    rows, cols = elev_data.shape
    color_data_3d = color_data.reshape((1, *color_data.shape))

    with rasterio.io.MemoryFile() as memfile:
        with memfile.open(
            driver='GTiff',
            height=color_data_3d.shape[1],
            width=color_data_3d.shape[2],
            count=1,
            dtype=color_data_3d.dtype,
            crs=color_meta['crs'],
            transform=color_meta['transform'],
        ) as dataset:
            dataset.write(color_data_3d)
            resampled = dataset.read(
                1,
                out_shape=(rows, cols),
                resampling=Resampling.average,
            )

    x, y = np.meshgrid(np.arange(cols), np.arange(rows))
    grid = pv.StructuredGrid(x, y, elev_data * elevation_scale)
    grid.point_data[scalar_name] = resampled.flatten(order='F')

    plotter = pv.Plotter()
    plotter.add_mesh(
        grid,
        scalars=scalar_name,
        cmap='YlGn',
        clim=[0, 1],
        lighting=True,
    )
    plotter.add_axes(interactive=True)
    plotter.show()
