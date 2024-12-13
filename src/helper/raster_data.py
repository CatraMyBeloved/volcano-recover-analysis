from dataclasses import dataclass
from enum import Enum
import numpy as np
import rasterio
from pathlib import Path

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

