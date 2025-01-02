from pathlib import Path

from seaborn._core.scales import Temporal

from src.data_processing import *
from src.helper.coordinate_transform import pixel_to_geographic, \
    geographic_to_pixel
from src.visualization import *
from src.helper import *


def main():
    calculator = RasterCalculator('data/processed',
                                  results_folder='/rasters')
    dates = year2018
    temp1_analysis = Timeseries(tile = 'T28RBS', dates=dates, bounds =
    'lavaflow_lapalma')

    temp1_analysis.calculate('savi', save_file=True)

    dates = year2019

    temp2_analysis = Timeseries(tile = 'T28RBS', dates=dates, bounds =
                                'lavaflow_lapalma')

    temp2_analysis.calculate('savi', save_file=True)

if __name__ == '__main__':
    main()

