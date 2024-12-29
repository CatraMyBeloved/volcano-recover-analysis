from dataclasses import dataclass
from enum import Enum
import numpy as np
import rasterio
from rasterio.windows import Window
from pathlib import Path
from typing import Any

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
    bounds : Any  = None
    read_with_window : bool = False
    window : rasterio.windows.Window = None

    def __post_init__(self):
        if self.source is not None:
            if self.read_with_window:
                with rasterio.open(self.source) as src:
                    self.data = src.read(1, window= self.window)
                    self.meta = src.profile.copy()
                    self.bounds = src.bounds
                    self.meta['height'] = self.window.height
                    self.meta['width'] = self.window.width
                    self.meta['transform'] = rasterio.windows.transform(
                        self.window, self.meta['transform'])
            else:
                with rasterio.open(self.source) as src:
                    self.data = src.read(1)
                    self.meta = src.profile.copy()
                    self.bounds = src.bounds
        self.meta['driver'] = 'GTiff'
        self.meta['dtype'] = 'float32'
    def save(self, path: str | Path):
        """Saves the raster data to a file using the stored metadata"""
        results_folder = Path('results')
        print(f'Trying to save to {path}')
        try:
            with rasterio.open(results_folder / path, 'w', **self.meta) as dst:
                dst.write(self.data, 1)
        except Exception as e:
            print(f'Failed to save to {path}: {e}')
