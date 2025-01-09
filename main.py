import matplotlib.pyplot as plt
from src.data_processing import *

from src.helper import *

from scipy.ndimage import generic_filter



def main():

    dates = year2019
    temp1_analysis = Timeseries(tile = 'T28RBS', dates=dates, bounds =
    'lapalma')

    matrix = temp1_analysis.create_timeseries_matrix('savi')

    temp1_analysis.create_clusters_matrix(n_clusters=5,save_raster=True)

if __name__ == '__main__':
    main()

