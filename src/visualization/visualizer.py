from pathlib import Path
from typing import Type

import matplotlib.pyplot as plt
import numpy as np
import rasterio
from matplotlib.colors import BoundaryNorm, ListedColormap



class Visualizer:
    def __init__(self):
        self.data = None
        self.colormaps = {
            'ndvi': 'RdYlGn',
            'savi': 'RdYlGn',
            'nbr': 'RdYlBu',
            'default': 'viridis',
            'std': 'magma',
            'mean': 'RdYlGn'
        }

        self.discrete_bounds = [-1, 0, 0.2, 0.4, 0.6, 0.8, 1]
        self.discrete_colors = ['red', 'orange', 'yellow', 'lightgreen',
                                'green', 'darkgreen']
        self.discrete_norm = BoundaryNorm(self.discrete_bounds,
                                          len(self.discrete_colors))

        self.default_style = {
            'figsize': (10, 8)}
        self.comp_style = {
            'figsize': (20, 8)
        }

    def _read_data(self, data: str | Path | np.ndarray,
                   band: int = 1) -> np.ndarray:
        if isinstance(data, Path):
            with rasterio.open(data) as src:
                return src.read(band)

        elif isinstance(data, np.ndarray):
            return data
        elif isinstance(data, str):
            file_path = Path(data)
            with rasterio.open(file_path) as src:
                return src.read(band)

        raise TypeError(
            f'Data must be a Path, a path string or a numpy array, '
            f'got {type(data).__name__}'
        )

    def simple_plot(self, data: str | Path | np.ndarray, band: int = 1,
                    title: str = None, index: str = 'default',
                    discrete: bool = False) -> plt.Figure:
        data = self._read_data(data, band)
        # Composites carry NaN where nothing was measurable; draw those as grey
        # rather than letting them read as a value.
        data = np.ma.masked_invalid(data)

        fig, ax = plt.subplots(**self.default_style)
        if discrete:
            palette = ListedColormap(self.discrete_colors)
            palette.set_bad('#d9d9d9')
            im = ax.imshow(data, cmap=palette, norm=self.discrete_norm)
        else:
            palette = plt.get_cmap(self.colormaps[index]).copy()
            palette.set_bad('#d9d9d9')
            im = ax.imshow(data, cmap=palette, vmin=-1, vmax=1)

        plt.colorbar(im, ax=ax)

        if title:
            plt.title(title)
        plt.show()
        return fig

    def compare_plots(self,
                      data1: str | Path | np.ndarray,
                      data2: str | Path | np.ndarray,
                      band: int = 1,
                      titles: tuple[str, str] = None,
                      index: str = 'default',
                      discrete: bool = False) \
            -> plt.Figure:
        data1 = np.ma.masked_invalid(self._read_data(data1, band))
        data2 = np.ma.masked_invalid(self._read_data(data2, band))

        fig, (ax1, ax2) = plt.subplots(1, 2, **self.comp_style)

        if discrete:
            palette = ListedColormap(self.discrete_colors)
        else:
            palette = plt.get_cmap(self.colormaps[index]).copy()
        palette.set_bad('#d9d9d9')

        if discrete:
            im1 = ax1.imshow(data1, cmap=palette, norm=self.discrete_norm)
            im2 = ax2.imshow(data2, cmap=palette, norm=self.discrete_norm)
        else:
            im1 = ax1.imshow(data1, cmap=palette, vmin=-1, vmax=1)
            im2 = ax2.imshow(data2, cmap=palette, vmin=-1, vmax=1)

        plt.colorbar(im1, ax=ax1)
        plt.colorbar(im2, ax=ax2)

        if titles:
            ax1.set_title(titles[0])
            ax2.set_title(titles[1])
        plt.show()
        return fig

    def subsampling(self, data:np.array, size: int) -> np.ndarray:
        rows = data.shape[0] // size
        cols = data.shape[1] // size
        data = data[:(rows*size), :(cols*size)]

        return data.reshape(rows, size, cols, size).mean(axis=(1,3))

