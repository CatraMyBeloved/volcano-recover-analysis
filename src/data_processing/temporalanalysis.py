import numpy as np
from datetime import datetime
import geopandas as gpd
import rasterio
from pathlib import Path
import matplotlib.pyplot as plt
from rasterio.windows import Window
from src.data_processing import RasterCalculator

class TemporalAnalysis:

    def __init__(self, tile, RasterCalculator, dates = None, bounds = None, results_folder = None):
        self.bounds = bounds
        self.tile = tile
        self.RasterCalculator = RasterCalculator
        if bounds != None:
            self.RasterCalculator.set_borders(self.bounds)
        self.results_folder = results_folder
        self.dates = []
        self.savi_series = []

        if dates is None:
            print('Please provide dates to examine using .add_date')
        else:
            self.add_dates(dates)

            self._initialize_savi_series()

    def _initialize_savi_series(self):
        for date in self.dates:
            date_str = date.strftime('%Y%m%d')
            if self.bounds is None:
                savi = self.RasterCalculator.calculate_savi(self.tile, date_str, use_bounds=False)
            else:
                savi = self.RasterCalculator.calculate_savi(self.tile, date_str, use_bounds=True)
            self.savi_series.append(savi)

    def add_date(self, date):
        date = datetime.strptime(date, '%Y%m%d')

        self.dates.append(date)

        date_str = datetime.strftime(date, '%Y%m%d')

        if self.bounds is None:
            savi = self.RasterCalculator.calculate_savi(self.tile, date_str, use_bounds=False)
        else:
            savi = self.RasterCalculator.calculate_savi(self.tile, date_str, use_bounds=True)

        self.savi_series.append(savi)

    def add_dates(self, dates):
        for date in dates:
            print(f'adding date: {date}')
            self.add_date(date)

    def _save_result(self, result, name, folder=None, use_bounds=False):
        if folder is None:
            folder = 'analysis_results'
        else:
            folder = Path(folder)

        original_file = self.RasterCalculator._selection(self.tile, datetime.strftime(self.dates[0], '%Y%m%d'), ['02'])[0]

        with rasterio.open(original_file) as src:
            metadata = src.profile.copy()

        project_directory = Path(__file__).parents[2]
        result_directory = project_directory / 'results' / folder

        result_directory.mkdir(parents=True, exist_ok=True)

        if not use_bounds:
            metadata.update(
                driver='GTiff',
                dtype='float32',
                count=1,
                nodata=None
            )
        else:
            new_transform = rasterio.windows.transform(self.bounds, metadata['transform'])
            metadata.update(
                driver='GTiff',
                dtype='float32',
                count=1,
                nodata=None,
                height=self.bounds.height,
                width=self.bounds.width,
                transform=new_transform
            )



        with rasterio.open(result_directory / f"{name}.tif", 'w', **metadata) as dst:
            dst.write(result, 1)


    def calculate_gen_mean(self):
        return np.mean([np.mean(savi) for savi in self.savi_series])

    def calculate_gen_std(self):
        return np.std([np.mean(savi) for savi in self.savi_series])

    def calculate_gen_var(self):
        return np.var([np.mean(savi) for savi in self.savi_series])


    def calculate_pixel_mean(self, save = False):
        savi_stack = np.stack(self.savi_series)
        pixel_mean = np.mean(savi_stack, axis = 0)
        if save:
            self._save_result(pixel_mean, f'{self.tile}_pixel_mean_{datetime.strftime(min(self.dates), '%Y%m%d')}_{datetime.strftime(max(self.dates), '%Y%m%d')}')
        return pixel_mean

    def calculate_pixel_std(self, save = False):
        savi_stack = np.stack(self.savi_series)
        pixel_std = np.std(savi_stack, axis = 0)
        if save:
            self._save_result(pixel_std, f'{self.tile}_pixel_std_{datetime.strftime(min(self.dates), '%Y%m%d')}_{datetime.strftime(max(self.dates), '%Y%m%d')}')

        return pixel_std

    def calculate_pixel_variance(self, save = False):
        savi_stack = np.stack(self.savi_series)
        pixel_variance = np.var(savi_stack, axis = 0)
        if save:
            self._save_result(pixel_variance, f'{self.tile}_pixel_var_{datetime.strftime(min(self.dates), '%Y%m%d')}_{datetime.strftime(max(self.dates), '%Y%m%d')}')

        return pixel_variance

    def calculate_scaled_std(self, save = False, A = 10, scale = 'sqrt'):
        standard_deviation = self.calculate_pixel_std(save = False)
        if scale == 'log':
            scaled_standard_deviation = A * np.log(standard_deviation)
        elif scale == 'sqrt':
            scaled_standard_deviation = A * np.sqrt(standard_deviation)
        else:
            print('invalid scale')
            return standard_deviation
        if save:
            self._save_result(scaled_standard_deviation, f'{self.tile}_pixel_std_{scale}scaled_{datetime.strftime(min(self.dates), '%Y%m%d')}_{datetime.strftime(max(self.dates), '%Y%m%d')}')

        return scaled_standard_deviation

    def get_general_stats(self):
        print('General Statistics')
        print(f'Overall mean: {self.calculate_gen_mean()}')
        print(f'Overall standard deviation: {self.calculate_gen_std()}')
        print(f'Overall variance: {self.calculate_gen_var()}')
        plt.plot(self.dates, [np.mean(savi) for savi in self.savi_series])
        plt.gcf().autofmt_xdate()
        plt.show()

