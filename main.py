from pathlib import Path

from seaborn._core.scales import Temporal

from src.data_processing import *
from src.visualization import *



def main():
    dem_1 = RasterData(source = 'data/DEM_raw/n28_w018_3arc_v2.tif')
    dem_1.rastertype = RasterType.ELEVATION
    dem_2 = RasterData(source = 'data/DEM_raw/n28_w019_3arc_v2.tif')
    dem_2.rastertype = RasterType.ELEVATION
    processor = DEMProcessor('EPSG:32628', raster_data_objects= (dem_1, dem_2))

    processor.prepare_rasters()

    result = processor.merge_rasters(0,1)
    result.save('data/DEM_merged/merged.tif')

if __name__ == '__main__':
    main()

