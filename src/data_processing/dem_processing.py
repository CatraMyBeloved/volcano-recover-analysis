from dataclasses import dataclass
from enum import Enum

import numpy as np
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
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
    source: str
    data: np.ndarray = None
    meta: dict = None
    state: RasterState = RasterState.RAW
    RasterType: RasterType = RasterType.RAW_BAND

    def __post_init__(self):
        with rasterio.open(self.source) as src:
            self.data = src.read(1)
            self.meta = src.profile.copy()


class DEMProcessor:

    def __init__(self, target_crs, raster_data_objects: tuple[RasterData]):

        for raster_data_object in raster_data_objects:
            if raster_data_object.RasterType != RasterType.ELEVATION:
                raise ValueError(
                    f'Expected ELEVATION raster type but got {raster_data_object.RasterType}')
        self.rasters = raster_data_objects

        self.target_crs = target_crs


    def _clean_raster(self, raster):
        mask = raster.data != raster.meta.nodata

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

        transform, width, height = calculate_default_transform(raster.meta[
                                                                   'crs'],
                                                               target_crs,
                                                               raster.meta[
                                                                   'width'],
                                                               raster.meta[
                                                                   'height'],
                                                               raster.meta[
                                                                   'bounds'])

        destination = np.zeros((height, width), dtype=raster.data.dtype)

        reproject(source=raster.data, destination=destination,
                  src_transform=raster.meta['transform'],
                  src_crs=raster.meta['crs'],
                  dst_transform=transform,
                  dst_crs=target_crs,
                  resampling=Resampling.bilinear)

        raster.data = destination
        raster.meta.update(
            {'crs': target_crs, 'transform': transform, 'width': width,
             'height': height})
        raster.state = RasterState.REPROJECTED


    def _validate_for_merge(self, raster1: RasterData, raster2: RasterData):

        if raster1.meta['crs'] != raster2.meta['crs']:
            raise ValueError(
                f'CRS mismatch: {raster1.meta["crs"]} != {raster2.meta["crs"]}')

        resolution1 = raster1.meta['transform'][0]
        resolution2 = raster2.meta['transform'][0]

        if resolution1 != resolution2:
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
        rasters_to_clean = [raster for raster in self.rasters if
                            raster.state == RasterState.RAW]

        for raster in rasters_to_clean:
            self._clean_raster(raster)

        rasters_to_reproject = [raster for raster in self.rasters if
                                raster.state == RasterState.CLEAN]

        for raster in rasters_to_reproject:
            self._reproject_raster(raster, self.target_crs)

    def merge_rasters(self, raster_index1: int, raster_index2: int):
        raster1 = self.rasters[raster_index1]
        raster2 = self.rasters[raster_index2]
        if self._validate_for_merge(raster1, raster2):
            pass

#TODO: actually merge rasters lmao

