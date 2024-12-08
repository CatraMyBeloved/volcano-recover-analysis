import numpy as np
import rasterio

with rasterio.open('data/DEM_raw/n28_w018_3arc_v2.tif') as src:
    print(src.bounds)
