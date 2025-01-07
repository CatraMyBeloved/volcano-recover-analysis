import rasterio
import numpy as np
from numpy.polynomial.polynomial import polyfit

from src.helper import *
from src.data_processing import *
from dataclasses import dataclass
from numpy.polynomial import Polynomial as Poly
class Timeseries:
    def __init__(self,tile, dates, bounds = None) -> None:
        self.tile = tile
        self.dates = dates
        self.bounds = bounds
        self.raw_data = None
        self.index_data = None
        self.matrix = None
        self.calculator = RasterCalculator('data/processed',
                                  results_folder='/rasters')
        if bounds is not None:
            self.calculator.set_borders(bounds)
        print(f'Timeseries initialized with {len(self.dates)} dates')
        print(f'Ready to create indices')
        self.meta = self.calculator.calculate_savi(self.tile, self.dates[0],
                                                          save_file = False,
                                                          use_bounds=True).meta


    def calculate(self, index, save_file = False):
        self.index_data = None
        temporary_list = []
        for date in self.dates:
            if self.bounds is not None:
                if index == 'savi':
                    data = self.calculator.calculate_savi(self.tile, date,
                                                          save_file = False,
                                                          use_bounds=True)
                    temporary_list.append(data.data)
                elif index == 'ndwi':
                    data = self.calculator.calculate_ndwi(self.tile, date,
                                                          save_file = False,
                                                          use_bounds=True)
                    temporary_list.append(data.data)
                elif index == 'ndvi':
                    data = self.calculator.calculate_ndvi(self.tile, date,
                                                          save_file = False,
                                                          use_bounds=True)

                    temporary_list.append(data.data)
                else:
                    print(f'{index} not implemented yet')
                    return

        if temporary_list:
            self.index_data = np.stack(temporary_list, axis = 0)
        mean = np.mean(self.index_data, axis = 0)
        std = 10* np.sqrt(np.std(self.index_data, axis = 0))
        meta = data.meta.copy()

        pixel_mean = RasterData(data = mean, meta = meta,
                                state= RasterState.CALCULATED,
                                rastertype= RasterType.INDEX)

        pixel_std = RasterData(data = std, meta = meta,
                               state= RasterState.CALCULATED,
                               rastertype= RasterType.INDEX)

        if save_file:
            pixel_mean.save(f'analysis_results/{self.dates[0]}_'
                            f'{self.dates[-1]}_{index}_mean.tif')
            pixel_std.save(f'analysis_results/{self.dates[0]}_'
                           f'{self.dates[-1]}_{index}_std.tif')

    def create_timeseries_matrix(self, index):
        temporary_list = []
        data_matrix = None
        for date in self.dates:
            if self.bounds is not None:
                if index == 'savi':
                    data = self.calculator.calculate_savi(self.tile, date,
                                                          save_file = False,
                                                          use_bounds=True)
                    temporary_list.append(data.data.flatten())
                elif index == 'ndwi':
                    data = self.calculator.calculate_ndwi(self.tile, date,
                                                          save_file = False,
                                                          use_bounds=True)
                    temporary_list.append(data.data.flatten())
                elif index == 'ndvi':
                    data = self.calculator.calculate_ndvi(self.tile, date,
                                                          save_file = False,
                                                          use_bounds=True)

                    temporary_list.append(data.data.flatten())
                else:
                    print(f'{index} not implemented yet')
                    return

        if temporary_list:
            data_matrix = np.stack(temporary_list, axis = 0).T
            data_matrix = self._clean_data_matrix(data_matrix, 0.3)
            self.matrix = data_matrix
        return data_matrix

    def _clean_data_matrix(self, data_matrix, threshold):
        data_matrix = data_matrix.copy()
        differences = data_matrix[:, 1:] - data_matrix[:, :-1]
        print(differences)
        pixel, timestep = np.where(differences > threshold)
        print(f'Difference matrix length: {len(differences)}')
        print(f'{len(pixel)} pixels above threshold')
        print(f'Portion of pixels above threshold: {len(pixel)/len(data_matrix)}')
        for pixel, timestep in zip(pixel, timestep):
            before_value = data_matrix[pixel, timestep]
            if timestep +2 >= data_matrix.shape[1]:
                after_value = before_value
            else:
                after_value = data_matrix[pixel, timestep + 2]
            data_matrix[pixel, timestep+1] = (before_value - after_value)/2

        return data_matrix

    def calculate_slopes(self, save_raster = False):
        x_axis = np.arange(0, self.matrix.shape[1])
        matrix = self.matrix.T
        slopes = polyfit(x_axis, matrix, 1)
        slope_raster = np.reshape(slopes, (self.meta['height'],
                                          self.meta['width']))
        slope_data = RasterData(data=slope_raster, meta=self.meta)

        if save_raster:
            slope_data.save(f'analysis_results/{self.dates[0]}_'
                            f'{self.dates[-1]}_slopes.tif')