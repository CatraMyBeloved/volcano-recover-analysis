from pathlib import Path

from seaborn._core.scales import Temporal

from src.data_processing import *
from src.visualization import *



def main():
    calculator = RasterCalculator('data/processed',
                                  results_folder='rasters')

    calculator.set_borders('lapalma')

    calculator.calculate_savi(tile= 'T28RBS', capture_date ='20220428',
                              save_file=True, use_bounds='lapalma')
    calculator.find_water(tile= 'T28RBS', capture_date ='20180708',
                              save_file=True, use_bounds='lapalma')


if __name__ == '__main__':
    main()

