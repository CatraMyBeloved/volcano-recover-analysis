import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.windows import Window
from rasterio.coords import BoundingBox
from rasterio.windows import from_bounds


import numpy as np

def reproject_crs(src_path, dst_path, dst_crs):

    with rasterio.open(src_path) as src:
        transform, width, height = calculate_default_transform(src.crs,
                                                               dst_crs,
                                                               src.width,
                                                               src.height,
                                                               *src.bounds)
        original_metadata = src.meta.copy()
        original_metadata.update({'crs': dst_crs, 'transform': transform,
                                  'width': width, 'height': height})

        with rasterio.open(dst_path, 'w', **original_metadata) as dst:
            for i in range(1, src.count + 1):
                reproject(source=rasterio.band(src, i),
                          destination=rasterio.band(dst, i),
                          src_transform=src.transform,
                          src_crs=src.crs,
                          dst_transform=transform,
                          dst_crs=dst_crs,
                          resampling=Resampling.bilinear)


def crop_intersection(dem_path, other_path, dst_path):
    with rasterio.open(dem_path) as dem_src:
        dem_bounds = dem_src.bounds
        dem_transform = dem_src.transform
    with rasterio.open(other_path) as other_src:
        other_bounds = other_src.bounds
        other_transform = other_src.transform

    intersection = (max(dem_bounds[0], other_bounds[0]),
                    max(dem_bounds[1], other_bounds[1]),
                    min(dem_bounds[2], other_bounds[2]),
                    min(dem_bounds[3], other_bounds[3]))

    fitting_window = from_bounds(*intersection, transform=dem_src.transform)

    with rasterio.open(other_path) as other_src, rasterio.open(dem_path) as dem_src:
        other_data = other_src.read(window=fitting_window)
        other_data_meta = other_src.profile.copy()
        dem_data = dem_src.read(window=fitting_window)
        dem_data_meta = dem_src.profile.copy()

    dem_transform = rasterio.windows.transform(fitting_window, dem_src.transform)

    other_transform = rasterio.windows.transform(fitting_window, other_src.transform)

    dem_data_meta.update({'transform': dem_transform,
                          'width': dem_data.shape[2],
                          'height': dem_data.shape[1]})
    with (rasterio.open(f'{dst_path}/dem_cropped.tif', 'w', **dem_data_meta) as
          dst):
        dst.write(dem_data, 1)

    other_data_meta.update({'transform': other_transform,
                           'width': other_data.shape[2],
                            'height': other_data.shape[1]})
    with rasterio.open(f'{dst_path}/other_cropped.tif', 'w', other_data_meta) as dst:
        dst.write(other_data, 1)

