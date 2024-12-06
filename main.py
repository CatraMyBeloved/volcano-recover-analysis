from pathlib import Path

from seaborn._core.scales import Temporal

from src.data_processing import *
from src.visualization import *



def main():
    merge_dem_tiles(['data/DEM_raw/n28_w018_3arc_v2.tif',
                     'data/DEM_raw/n28_w019_3arc_v2.tif'],
                    'data/DEM_merged/lapalma_dem.tif'
                    )

    reproject_crs('data/DEM_merged/lapalma_dem.tif',
                  'data/DEM_merged/lapalma_dem_reprojected.tif', 'EPSG:32628')

    crop_intersection('data/DEM_merged/lapalma_dem_reprojected.tif',
                      'results/rasters/T28RBS_20180807_savi_crop.tif', dst_path=
                      'data/DEM_finished')

if __name__ == '__main__':
    main()

