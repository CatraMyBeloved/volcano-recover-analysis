from pathlib import Path

from seaborn._core.scales import Temporal

from src.data_processing import *
from src.visualization import *



def main():
    merge_dem_tiles(['data/DEM_raw/n28_w018_3arc_v2.tif',
                     'data/DEM_raw/n28_w019_3arc_v2.tif'],
                    'data/DEM_merged/lapalma_dem.tif'
                    )

if __name__ == '__main__':
    main()

