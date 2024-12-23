from pathlib import Path

from seaborn._core.scales import Temporal

from src.data_processing import *
from src.helper.coordinate_transform import pixel_to_geographic, \
    geographic_to_pixel
from src.visualization import *
from src.helper import *


def main():
    calculator = RasterCalculator('data/processed',
                                  results_folder='results/rasters')

    calculator.set_borders('lapalma')
    calculator.calculate_savi('T28RBS', capture_date='20180807',
                              save_file=True, use_bounds=True)





if __name__ == '__main__':
    main()

