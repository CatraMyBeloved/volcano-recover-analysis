import numpy as np
import rasterio
from rasterio.windows import Window

with rasterio.open('data/DEM_merged/merged_30.tif') as src:
    borders = Window(393, 340, 3698-393, 5148-340)
    data = src.read(1, window = borders)
    print(len(data[np.where(data > 10)]))
