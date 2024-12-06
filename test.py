import rasterio
import numpy as np

with rasterio.open('data/DEM_raw/n28_w018_3arc_v2.tif') as src:
    data = src.read(1)
    print(f"Min value: {np.min(data[data != src.nodata])}")
    print(f"Max value: {np.max(data[data != src.nodata])}")
    print(f"No data value: {src.nodata}")

with rasterio.open('data/DEM_raw/n28_w019_3arc_v2.tif') as src:
    data = src.read(1)
    print(f"Min value: {np.min(data[data != src.nodata])}")
    print(f"Max value: {np.max(data[data != src.nodata])}")
    print(f"No data value: {src.nodata}")