import numpy as np
import rasterio

with rasterio.open('data/processed/T28RBS/20180713/R10m/T28RBS_20180713T120319_AOT_10m.jp2') as src:
    print(src.profile['crs'])
