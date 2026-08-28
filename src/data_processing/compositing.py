"""Per-pixel median composites of a spectral index over a set of acquisitions.

A composite answers "what did this pixel look like during this period" using
only the observations where the pixel was actually measurable. That is the
difference that matters against picking one attractive scene: cloud on any
single date is common here, but it moves between dates, so almost every pixel
has several clear looks across a season even when no single scene is clear.

The median is used rather than the mean because it is unmoved by the occasional
bright pixel a cloud mask missed, and because contamination that survives
masking is one-sided: thin cirrus and haze raise reflectance, they do not lower
it, so a mean would drift upward while a median would not.

Every composite carries a count raster. Pixels with few observations are not
wrong, but they are less certain, and a composite that hides how thin it is in
places invites conclusions the data cannot support.
"""
import warnings
from pathlib import Path

import numpy as np
from sklearn.cluster import KMeans

from src.data_processing.raster_calculator import RasterCalculator
from src.helper.product_metadata import crs_for_tile
from src.helper.raster_data import RasterData, RasterState, RasterType


class Compositor:
    """Builds masked median composites for named periods."""

    def __init__(
        self,
        tile: str,
        band_dir: str = 'data/processed',
        results_folder: str = 'analysis_results',
        bounds: str | tuple | None = None,
    ) -> None:
        self.tile = tile
        self.results_folder = results_folder
        self.bounds = bounds
        self.calculator = RasterCalculator(band_dir, results_folder)
        if bounds is not None:
            self.calculator.set_borders(bounds)

    def _stack(self, dates: list[str], index: str) -> np.ndarray:
        """Masked index values for every date, shaped (dates, rows, cols)."""
        frames = [
            self.calculator.masked_index(
                self.tile, date, index=index, use_bounds=self.bounds is not None
            )
            for date in dates
        ]
        return np.stack(frames, axis=0)

    def composite(
        self,
        dates: list[str],
        index: str = 'savi',
        min_observations: int = 1,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return (median composite, observation count) for `dates`.

        Pixels with fewer than `min_observations` clear looks are left NaN
        rather than filled, so they stay visible as gaps downstream.
        """
        if not dates:
            raise ValueError('composite needs at least one date')

        stack = self._stack(dates, index)
        counts = np.sum(np.isfinite(stack), axis=0).astype('float32')

        # nanmedian warns on all-NaN pixels and returns NaN for them, which is
        # the wanted behaviour; only the warning is suppressed.
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', RuntimeWarning)
            median = np.nanmedian(stack, axis=0).astype('float32')

        median = np.where(counts >= min_observations, median, np.nan)
        return median, counts

    def composite_raster(
        self,
        dates: list[str],
        index: str = 'savi',
        min_observations: int = 1,
        label: str | None = None,
        save: bool = False,
    ) -> tuple[RasterData, RasterData]:
        """Composite as georeferenced rasters, optionally written to disk."""
        median, counts = self.composite(dates, index, min_observations)
        meta = self.calculator.calculate_ndvi(
            self.tile, dates[0], save_file=False,
            use_bounds=self.bounds is not None,
        ).meta

        # The source JP2s carry no CRS, so the transform alone would leave the
        # output unplaceable on a map. Supply it from the tile's UTM zone.
        if not meta.get('crs'):
            meta = {**meta, 'crs': crs_for_tile(self.tile)}
        meta['nodata'] = float('nan')

        composite = RasterData(
            data=median, meta=meta,
            state=RasterState.CALCULATED, rastertype=RasterType.INDEX,
        )
        observations = RasterData(
            data=counts, meta=meta,
            state=RasterState.CALCULATED, rastertype=RasterType.INDEX,
        )

        if save:
            stem = label or f'{dates[0]}_{dates[-1]}'
            folder = Path(self.results_folder)
            composite.save(folder / f'{stem}_{index}_median.tif')
            observations.save(folder / f'{stem}_{index}_count.tif')

        return composite, observations

    def cluster_periods(
        self,
        periods: dict[str, list[str]],
        index: str = 'ndvi',
        n_clusters: int = 5,
        min_observations: int = 2,
        random_state: int = 42,
        save: bool = False,
    ) -> tuple[RasterData, list[list[float]]]:
        """Cluster pixels by their composite value in each period.

        Clustering the raw date-by-date trajectory does not work on a dataset
        built from a few seasonal windows: the dates arrive in near-simultaneous
        clumps separated by years, so most of the variance between adjacent
        columns is weather, not recovery, and no pixel is clear on every date,
        which leaves K-means nothing complete to work with.

        One composite per period is both denser and closer to the question. A
        pixel's signature becomes its value before the eruption, after it, and
        now, which is the recovery pattern itself.

        Returns the label raster and the cluster centres. Labels are ordered by
        first-period value so that a given label means the same thing from one
        run to the next; pixels missing any period are labelled -1.
        """
        labels_in_order = list(periods)
        stack = np.stack(
            [
                self.composite(periods[label], index, min_observations)[0]
                for label in labels_in_order
            ],
            axis=0,
        )
        rows, cols = stack.shape[1], stack.shape[2]
        features = stack.reshape(len(labels_in_order), -1).T

        complete = np.isfinite(features).all(axis=1)
        share = 100.0 * np.count_nonzero(complete) / complete.size
        print(f'clustering {share:.2f}% of pixels present in all '
              f'{len(labels_in_order)} periods; the rest are labelled -1')
        if not complete.any():
            raise RuntimeError('no pixel has a composite in every period')

        clustering = KMeans(n_clusters=n_clusters, random_state=random_state)
        raw = clustering.fit_predict(features[complete])

        # Relabel by ascending first-period value so labels are stable and
        # readable rather than arbitrary K-means output order.
        order = np.argsort(clustering.cluster_centers_[:, 0])
        remap = np.empty(n_clusters, dtype='int64')
        remap[order] = np.arange(n_clusters)

        labels = np.full(features.shape[0], -1, dtype='float32')
        labels[complete] = remap[raw]

        meta = self.calculator.calculate_ndvi(
            self.tile, periods[labels_in_order[0]][0], save_file=False,
            use_bounds=self.bounds is not None,
        ).meta
        if not meta.get('crs'):
            meta = {**meta, 'crs': crs_for_tile(self.tile)}
        meta['nodata'] = -1.0

        raster = RasterData(
            data=labels.reshape(rows, cols), meta=meta,
            state=RasterState.CALCULATED,
        )
        if save:
            raster.save(Path(self.results_folder) / f'clusters_{index}_{n_clusters}.tif')

        centres = clustering.cluster_centers_[order].tolist()
        return raster, centres

    def summarise(
        self,
        dates: list[str],
        index: str,
        label: str,
        min_observations: int = 1,
    ) -> dict:
        """Report what a composite rests on, for the record and for captions.

        `min_observations` must match the value used to build the raster being
        described, or the reported coverage will not be the coverage on disk.
        """
        median, counts = self.composite(dates, index, min_observations)
        total = counts.size
        finite = np.isfinite(median)
        return {
            'label': label,
            'scenes': len(dates),
            'dates': list(dates),
            'index': index,
            'min_observations_required': min_observations,
            'median_observations': float(np.median(counts)),
            'min_observations': int(counts.min()),
            'pixels_with_no_observation': float(
                100.0 * np.count_nonzero(counts == 0) / total
            ),
            'pixels_composited': float(100.0 * np.count_nonzero(finite) / total),
            'median_value': float(np.nanmedian(median)) if finite.any() else float('nan'),
        }
