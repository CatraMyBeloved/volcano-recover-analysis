from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import Affine
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.coords import BoundingBox
from scipy.interpolate import LinearNDInterpolator


class RasterState(Enum):
    RAW = 'raw'
    CLEAN = 'clean'
    MERGED = 'merged'
    REPROJECTED = 'reprojected'
    CROPPED = 'cropped'
    CALCULATED = 'calculated'

    def __str__(self):
        return self.value


class RasterType(Enum):
    ELEVATION = 'elevation'
    RAW_BAND = 'raw_band'
    INDEX = 'index'

    def __str__(self):
        return self.value


@dataclass
class RasterData:
    source: str = None
    data: np.ndarray = None
    meta: dict = None
    state: RasterState = RasterState.RAW
    rastertype: RasterType = RasterType.RAW_BAND
    bounds = None

    def __post_init__(self):
        if self.source is not None:
            with rasterio.open(self.source) as src:
                self.data = src.read(1)
                self.meta = src.profile.copy()
                self.bounds = src.bounds

    def save(self, path: str | Path):
        """Saves the raster data to a file using the stored metadata"""
        with rasterio.open(path, 'w', **self.meta) as dst:
            dst.write(self.data, 1)


class DEMProcessor:

    def __init__(self, target_crs, raster_data_objects: tuple[RasterData, ...]):

        for raster_data_object in raster_data_objects:
            if raster_data_object.rastertype != RasterType.ELEVATION:
                raise ValueError(
                    f'Expected ELEVATION raster type but got '
                    f'{raster_data_object.rastertype}')
        self.rasters = raster_data_objects

        self.target_crs = target_crs

    def _clean_raster(self, raster):
        mask = raster.data != raster.meta['nodata']

        rows, cols = np.where(mask)

        values = raster.data[rows, cols]

        points = np.column_stack((rows, cols))
        interpolator = LinearNDInterpolator(points, values)

        grid_rows, grid_cols = np.mgrid[0:raster.data.shape[0],
                               0:raster.data.shape[1]]
        interpolated_values = interpolator((grid_rows, grid_cols))

        raster.data[~mask] = interpolated_values[~mask]
        raster.state = RasterState.CLEAN

    def _reproject_raster(self, raster, target_crs):
        with rasterio.open('temp/temp_raster.tif', 'w', **raster.meta) as dst:
            dst.write(raster.data, 1)

        with rasterio.open('temp/temp_raster.tif') as src:
            transform, width, height = calculate_default_transform(src.crs,
                                                                   target_crs,
                                                                   src.width,
                                                                   src.height,
                                                                   *src.bounds)
            original_metadata = src.meta.copy()
            original_metadata.update({'crs': target_crs, 'transform': transform,
                                      'width': width, 'height': height})

            with rasterio.open('temp/temp_raster_reproj.tif', 'w', **original_metadata) as dst:
                for i in range(1, src.count + 1):
                    reproject(source=rasterio.band(src, i),
                              destination=rasterio.band(dst, i),
                              src_transform=src.transform,
                              src_crs=src.crs,
                              dst_transform=transform,
                              dst_crs=target_crs,
                              resampling=Resampling.bilinear)

        result = RasterData(source = 'temp/temp_raster_reproj.tif')
        result.rastertype = RasterType.ELEVATION
        result.state = RasterState.REPROJECTED

        return result
    def _validate_for_merge(self, raster1: RasterData, raster2: RasterData):

        if raster1.meta['crs'] != raster2.meta['crs']:
            raise ValueError(
                f'CRS mismatch: {raster1.meta["crs"]} != {raster2.meta["crs"]}')

        resolution1 = raster1.meta['transform'][0]
        resolution2 = raster2.meta['transform'][0]

        if not np.isclose(resolution1, resolution2, rtol=0.02):
            raise ValueError(
                f'Resolution mismatch: {resolution1} != {resolution2}')

        if raster1.meta['dtype'] != raster2.meta['dtype']:
            raise ValueError(
                f'Data type missmatch: {raster1.meta["dtype"]} != {raster2.meta["dtype"]}')

        if raster1.state != raster2.state:
            raise ValueError(f'State mismatch: {raster1.state} != '
                             f'{raster2.state}')

        return True

    def prepare_rasters(self):
        print(f'Choosing rasters to clean')
        rasters_to_clean = [raster for raster in self.rasters if
                            raster.state == RasterState.RAW]

        print(f'Cleaning {len(rasters_to_clean)} rasters')

        counter = 0
        for raster in rasters_to_clean:
            counter += 1
            print(f'Raster {counter}/{len(rasters_to_clean)} being cleaned...')
            self._clean_raster(raster)

        print(f'Cleaned {len(rasters_to_clean)} rasters')
        print(f'Choosing rasters to reproject')

        rasters_to_reproject = [raster for raster in self.rasters if
                                raster.state == RasterState.CLEAN]

        print(f'Reprojecting {len(rasters_to_reproject)} rasters')

        counter = 0

        for raster in rasters_to_reproject:
            counter += 1
            print(
                f'Raster {counter}/{len(rasters_to_reproject)} being reprojected...')

            self._reproject_raster(raster, self.target_crs)

    def merge_rasters(self, raster_index1: int, raster_index2: int):
        print(f'Merging rasters...')
        raster1 = self.rasters[raster_index1]
        raster2 = self.rasters[raster_index2]
        print(f'Validating rasters...')
        if self._validate_for_merge(raster1, raster2):
            pass

        new_metadata = raster1.meta.copy()

        new_bounds = [
            min(raster1.bounds[0], raster2.bounds[0]),  # left
            min(raster1.bounds[1], raster2.bounds[1]),  # bottom
            max(raster1.bounds[2], raster2.bounds[2]),  # right
            max(raster1.bounds[3], raster2.bounds[3])  # top
        ]

        print(f'New bounds: {new_bounds}')

        resolution = raster1.meta['transform'][0]

        print(f'Resolution: {resolution}')

        new_width_m = new_bounds[2] - new_bounds[0]
        new_height_m = new_bounds[3] - new_bounds[1]
        print(f'New dimensions in m: {new_width_m, new_height_m}')
        new_width_pix = int(new_width_m / resolution) +1
        new_height_pix = int(new_height_m / resolution) +1
        print(f'New dimensions in pixels: {new_width_pix, new_height_pix}')
        print(f'Creating new ndarray')
        new_data = np.empty((new_height_pix, new_width_pix),
                            dtype=raster1.data.dtype)
        new_data[:] = raster1.meta['nodata']
        print(f'New raster: {new_data.shape}')

        print(f'Calculating offsets')
        raster1_offset_x = int((raster1.bounds[0] - new_bounds[0])/resolution)
        raster1_offset_y = int((raster1.bounds[1] - new_bounds[1])/resolution)

        raster2_offset_x = int((raster2.bounds[0] - new_bounds[0])/resolution)
        raster2_offset_y = int((raster2.bounds[1] - new_bounds[1])/resolution)

        raster1_size = (int(raster1.meta['height']),
                        int(raster1.meta['width']))
        raster2_size = (int(raster2.meta['height']),
                       int(raster2.meta['width']))

        # set data into new raster
        print(f'Adding new data')
        # raster1
        x_start_1 = raster1_offset_x
        x_end_1 = raster1_offset_x + raster1_size[1]
        y_start_1 = raster1_offset_y
        y_end_1 = raster1_offset_y + raster1_size[0]
        x_start_2 = raster2_offset_x
        x_end_2 = raster2_offset_x + raster2_size[1]
        y_start_2 = raster2_offset_y
        y_end_2 = raster2_offset_y + raster2_size[0]

        print("Slice dimensions:")
        print(f"y slice size1: {y_end_1 - y_start_1}")
        print(f"x slice size1: {x_end_1 - x_start_1}")
        print(f"y slice size2: {y_end_2 - y_start_2}")
        print(f"x slice size2: {x_end_2 - x_start_2}")
        print(f'raster1 bounds: {raster1.bounds}')
        print(f'raster2 bounds: {raster2.bounds}')
        print(f'new bounds: {new_bounds}')
        print('\nDoes it fit?')
        print(f'Target array shape: {new_data.shape}')
        print(f'Pasting data 1 into: {(y_start_1,y_end_1), (x_start_1,x_end_1)}')
        print(f'data 1 shape: {raster1.data.shape}')
        print(f'Pasting data 2 into: {(y_start_2,y_end_2), (x_start_2,x_end_2)}')
        print(f'data 2 shape: {raster2.data.shape}')

        new_data[y_start_1:y_end_1, x_start_1:x_end_1] = raster1.data
        new_data[y_start_2:y_end_2, x_start_2:x_end_2 ] = raster2.data
        print(f'Data added')
        print(f'Updating new metadata')
        # update meta data
        new_transform = Affine(a=raster1.meta['transform'][0],
                               b=0.0,
                               c=new_bounds[0],
                               d=0.0,
                               e=raster1.meta['transform'][4],
                               f=new_bounds[3]
                               )

        new_metadata.update({'width': new_width_pix,
                             'height': new_height_pix,
                             'transform': new_transform})

        new_raster = RasterData(data=new_data, meta=new_metadata)
        new_raster.rastertype = RasterType.ELEVATION
        new_raster.state = RasterState.MERGED
        print('Merge finished')
        return new_raster
