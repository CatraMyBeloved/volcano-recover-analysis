import numpy as np
from numpy.polynomial.polynomial import polyfit
from sklearn.cluster import KMeans

from src.helper.raster_data import RasterData, RasterState, RasterType
from src.data_processing.raster_calculator import RasterCalculator


class Timeseries:
    def __init__(self, tile: str, dates: list[str], bounds: str | tuple | None = None) -> None:
        self.tile = tile
        self.dates = dates
        self.bounds = bounds
        self.index_data: np.ndarray | None = None
        self.matrix: np.ndarray | None = None
        self.calculator = RasterCalculator('data/processed', results_folder='rasters')
        if bounds is not None:
            self.calculator.set_borders(bounds)
        self.meta = self.calculator.calculate_savi(
            self.tile, self.dates[0], save_file=False, use_bounds=bounds is not None
        ).meta
        print(f'Timeseries initialized with {len(self.dates)} dates')

    def _compute_index(self, index: str, date: str) -> RasterData:
        dispatch = {
            'savi': self.calculator.calculate_savi,
            'ndvi': self.calculator.calculate_ndvi,
            'ndwi': self.calculator.calculate_ndwi,
        }
        if index not in dispatch:
            raise ValueError(f"Index '{index}' is not implemented. Choose from: {list(dispatch)}")
        return dispatch[index](self.tile, date, save_file=False, use_bounds=self.bounds is not None)

    def calculate(self, index: str, save_file: bool = False) -> tuple[RasterData, RasterData]:
        frames = [self._compute_index(index, date) for date in self.dates]
        self.index_data = np.stack([f.data for f in frames], axis=0)
        mean = np.mean(self.index_data, axis=0)
        std = 10 * np.sqrt(np.std(self.index_data, axis=0))
        meta = frames[-1].meta

        pixel_mean = RasterData(data=mean, meta=meta,
                                state=RasterState.CALCULATED, rastertype=RasterType.INDEX)
        pixel_std = RasterData(data=std, meta=meta,
                               state=RasterState.CALCULATED, rastertype=RasterType.INDEX)

        if save_file:
            pixel_mean.save(f'analysis_results/{self.dates[0]}_{self.dates[-1]}_{index}_mean.tif')
            pixel_std.save(f'analysis_results/{self.dates[0]}_{self.dates[-1]}_{index}_std.tif')
        return pixel_mean, pixel_std

    def create_timeseries_matrix(self, index: str) -> np.ndarray:
        flattened = [self._compute_index(index, date).data.flatten() for date in self.dates]
        data_matrix = np.stack(flattened, axis=0).T
        self.matrix = self._clean_data_matrix(data_matrix, threshold=-0.2)
        return self.matrix

    def _clean_data_matrix(self, data_matrix: np.ndarray, threshold: float) -> np.ndarray:
        # Inter-date differences below threshold flag suspected cloud / shadow
        # contamination; the post-drop value is replaced by the mean of its
        # neighbors. Assumes contamination spans a single timestep.
        data_matrix = data_matrix.copy()
        differences = data_matrix[:, 1:] - data_matrix[:, :-1]
        pixel_idx, timestep_idx = np.where(differences < threshold)

        print(f'Inter-date differences: {differences.size}')
        print(f'{len(pixel_idx)} drops below threshold {threshold} '
              f'({len(pixel_idx) / data_matrix.size:.2%} of pixel-timesteps)')

        for pixel, timestep in zip(pixel_idx, timestep_idx):
            before = data_matrix[pixel, timestep]
            if timestep + 2 >= data_matrix.shape[1]:
                after = before
            else:
                after = data_matrix[pixel, timestep + 2]
            data_matrix[pixel, timestep + 1] = (before + after) / 2

        return data_matrix

    def calculate_slopes(self, save_raster: bool = False) -> RasterData:
        x_axis = np.arange(self.matrix.shape[1])
        coefficients = polyfit(x_axis, self.matrix.T, 1)
        slope_raster = coefficients[1].reshape((self.meta['height'], self.meta['width']))
        slope_data = RasterData(data=slope_raster, meta=self.meta, state=RasterState.CALCULATED)
        if save_raster:
            slope_data.save(f'analysis_results/{self.dates[0]}_{self.dates[-1]}_slopes.tif')
        return slope_data

    def create_clusters_matrix(
        self,
        n_clusters: int,
        random_state: int = 42,
        save_raster: bool = False,
    ) -> RasterData:
        clustering = KMeans(n_clusters=n_clusters, random_state=random_state)
        labels = clustering.fit_predict(self.matrix)
        labels_2d = labels.reshape((self.meta['height'], self.meta['width']))

        cluster_raster = RasterData(data=labels_2d, meta=self.meta, state=RasterState.CALCULATED)
        if save_raster:
            cluster_raster.save(f'analysis_results/{self.dates[0]}_{self.dates[-1]}_clusters.tif')
        return cluster_raster

    def fit_polynomial(self, degree: int = 2) -> np.ndarray:
        x_axis = np.arange(self.matrix.shape[1])
        return polyfit(x_axis, self.matrix.T, degree)
