import rasterio
import numpy as np
from src.helper import *
from src.data_processing import *
from dataclasses import dataclass

class Timeseries:
    def __init__(self,tile, dates, bounds = None) -> None:
        self.tile = tile
        self.dates = dates
        self.bounds = bounds
        self.raw_data = None
        self.index_data = None
        self.calculator = RasterCalculator('data/processed',
                                  results_folder='/rasters')
        if bounds is not None:
            self.calculator.set_borders(bounds)
        print(f'Timeseries initialized with {len(self.dates)} dates')
        print(f'Ready to create indices')


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
