import warnings
from datetime import datetime

import numpy as np
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
        """Unmasked index for one date. Use `calculator.masked_index` for values.

        Retained only for the georeferencing metadata, which the mask does not
        affect. Anything reading `.data` from this bypasses cloud masking.
        """
        dispatch = {
            'savi': self.calculator.calculate_savi,
            'ndvi': self.calculator.calculate_ndvi,
            'ndwi': self.calculator.calculate_ndwi,
        }
        if index not in dispatch:
            raise ValueError(f"Index '{index}' is not implemented. Choose from: {list(dispatch)}")
        return dispatch[index](self.tile, date, save_file=False, use_bounds=self.bounds is not None)

    def calculate(self, index: str, save_file: bool = False) -> tuple[RasterData, RasterData]:
        """Per-pixel mean and spread of the index across all dates."""
        self.index_data = np.stack(
            [
                self.calculator.masked_index(
                    self.tile, date, index=index, use_bounds=self.bounds is not None
                )
                for date in self.dates
            ],
            axis=0,
        )
        # Masked pixels must not count toward either statistic.
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)
            mean = np.nanmean(self.index_data, axis=0)
            std = np.nanstd(self.index_data, axis=0)
        meta = self._compute_index(index, self.dates[-1]).meta

        pixel_mean = RasterData(data=mean, meta=meta,
                                state=RasterState.CALCULATED, rastertype=RasterType.INDEX)
        pixel_std = RasterData(data=std, meta=meta,
                               state=RasterState.CALCULATED, rastertype=RasterType.INDEX)

        if save_file:
            pixel_mean.save(f'analysis_results/{self.dates[0]}_{self.dates[-1]}_{index}_mean.tif')
            pixel_std.save(f'analysis_results/{self.dates[0]}_{self.dates[-1]}_{index}_std.tif')
        return pixel_mean, pixel_std

    def create_timeseries_matrix(self, index: str) -> np.ndarray:
        """Build the pixel-by-date matrix, with unmeasurable pixels as NaN.

        Contaminated pixels are marked missing, not replaced. The previous
        approach flagged any inter-date drop beyond a threshold as cloud and
        substituted the mean of the neighbouring dates. Two things were wrong
        with that. It cannot distinguish contamination from a real event, so on
        this dataset it interpolated across the eruption itself and pulled the
        first post-eruption date up by 0.073 NDVI, toward the pre-eruption
        state. And the substitute is an invented number that is
        indistinguishable downstream from a measurement.

        The scene classification already records which pixels are cloud,
        shadow, cirrus or snow, per pixel and per date, so it is used instead of
        being inferred from the index.
        """
        flattened = [
            self.calculator.masked_index(
                self.tile, date, index=index, use_bounds=self.bounds is not None
            ).flatten()
            for date in self.dates
        ]
        self.matrix = np.stack(flattened, axis=0).T

        observations = np.isfinite(self.matrix).sum(axis=1)
        total = self.matrix.shape[0]
        print(f'{np.isnan(self.matrix).sum() / self.matrix.size:.2%} of '
              f'pixel-timesteps masked as unmeasurable')
        print(f'observations per pixel: median {np.median(observations):.0f} '
              f'of {len(self.dates)}, '
              f'{100 * np.count_nonzero(observations == 0) / total:.2f}% have none')
        return self.matrix

    def _decimal_years(self) -> np.ndarray:
        """Acquisition dates as years from the first, for fitting against time.

        Fitting against position in the list treats every gap as equal. These
        dates are four seasonal windows separated by up to three years, so
        position is not time and a slope taken against it is not a rate.
        """
        parsed = [datetime.strptime(date, '%Y%m%d') for date in self.dates]
        origin = parsed[0]
        return np.array(
            [(date - origin).days / 365.25 for date in parsed], dtype='float64'
        )

    def calculate_slopes(
        self, save_raster: bool = False, min_observations: int = 4
    ) -> RasterData:
        """Per-pixel linear trend in index units per year.

        Solved in closed form per pixel over that pixel's finite observations,
        because a shared design matrix cannot be used when each pixel has its
        own pattern of missing dates. Pixels with fewer than
        `min_observations` are left NaN rather than fitted through noise.
        """
        if self.matrix is None:
            raise RuntimeError('call create_timeseries_matrix before calculate_slopes')

        years = self._decimal_years()
        values = self.matrix
        weights = np.isfinite(values)
        filled = np.where(weights, values, 0.0)

        count = weights.sum(axis=1)
        sum_x = (weights * years).sum(axis=1)
        sum_y = filled.sum(axis=1)
        sum_xx = (weights * years ** 2).sum(axis=1)
        sum_xy = (filled * years).sum(axis=1)

        denominator = count * sum_xx - sum_x ** 2
        with np.errstate(divide='ignore', invalid='ignore'):
            slope = (count * sum_xy - sum_x * sum_y) / denominator
        slope = np.where(
            (count >= min_observations) & (denominator > 0), slope, np.nan
        )

        print(f'slopes fitted for '
              f'{100 * np.count_nonzero(np.isfinite(slope)) / slope.size:.2f}% '
              f'of pixels (needing {min_observations} or more observations)')

        slope_raster = slope.reshape(
            (self.meta['height'], self.meta['width'])
        ).astype('float32')
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
        """Cluster pixels by their full trajectory.

        K-means has no notion of a missing value, and every imputation choice
        would decide the answer for the pixels it invents values for. Only
        pixels observed on every date are clustered; the rest are labelled -1
        so a gap stays legible as a gap rather than joining a cluster it was
        never measured into.
        """
        complete = np.isfinite(self.matrix).all(axis=1)
        share = 100.0 * np.count_nonzero(complete) / complete.size
        print(f'clustering {share:.2f}% of pixels with a value on all '
              f'{len(self.dates)} dates; the rest are labelled -1')
        if not complete.any():
            raise RuntimeError(
                'No pixel is clear on every date, so there is nothing complete '
                'to cluster. This is expected for a set of seasonal windows '
                'rather than a dense series. Cluster per-period composites '
                'instead: uv run scripts/build_composites.py --clusters 5'
            )

        clustering = KMeans(n_clusters=n_clusters, random_state=random_state)
        labels = np.full(self.matrix.shape[0], -1, dtype='float32')
        labels[complete] = clustering.fit_predict(self.matrix[complete])
        labels_2d = labels.reshape((self.meta['height'], self.meta['width']))

        cluster_raster = RasterData(data=labels_2d, meta=self.meta, state=RasterState.CALCULATED)
        if save_raster:
            cluster_raster.save(f'analysis_results/{self.dates[0]}_{self.dates[-1]}_clusters.tif')
        return cluster_raster
