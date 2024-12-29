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
    dates = [
        '20190213',
        '20190223',
        '20190310',
        '20190414',
        '20190524',
        '20190603',
        '20190713',
        '20190723',
        '20190812',
        '20190901',
        '20191001',
        '20191031',
        '20191130',
    ]
    temp_analysis = Timeseries(tile = 'T28RBS', dates=dates, bounds = 'lapalma')


    temp_analysis.calculate('savi', save_file=True)

if __name__ == '__main__':
    main()

