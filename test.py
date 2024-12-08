import numpy as np
import rasterio


with rasterio.open('raster2_1.tif') as src:
    data = src.read(1)
    print(data.min(), data.max())


with rasterio.open('raster2_2.tif') as src:
    data = src.read(1)
    print(data.min(), data.max())
