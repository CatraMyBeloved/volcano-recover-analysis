from pathlib import Path

import numpy as np
from numpy.polynomial.polynomial import polyfit
from seaborn._core.scales import Temporal
from src.data_processing import *
from src.helper.coordinate_transform import pixel_to_geographic, \
    geographic_to_pixel
from src.visualization import *
from src.helper import *
from numpy.polynomial import Polynomial as Poly



def main():

    dates = year2019
    temp1_analysis = Timeseries(tile = 'T28RBS', dates=dates, bounds =
    'lapalma')

    matrix = temp1_analysis.create_timeseries_matrix('savi')

    print(f'Matrix :{matrix}')
    print(f'Matrix shape: {matrix.shape}')


if __name__ == '__main__':
    main()

