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
from scipy.cluster.hierarchy import dendrogram, linkage
import matplotlib.pyplot as plt
from sklearn.cluster import AgglomerativeClustering
from sklearn.cluster import MiniBatchKMeans
from sklearn.cluster import KMeans



def main():

    dates = year2019
    temp1_analysis = Timeseries(tile = 'T28RBS', dates=dates, bounds =
    'lapalma')

    matrix = temp1_analysis.create_timeseries_matrix('savi')

    clustering = KMeans(n_clusters=6, random_state= 42)
    labels = clustering.fit_predict(matrix)
    labels_2d = labels.reshape((temp1_analysis.meta['height'], temp1_analysis.meta[
        'width']))

    cluster_raster = RasterData(
        data=labels_2d,
        meta=temp1_analysis.meta,
        state=RasterState.CALCULATED
    )
    cluster_raster.save('analysis_results/clusters.tif')


if __name__ == '__main__':
    main()

