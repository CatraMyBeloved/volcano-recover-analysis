# Volcanic Recovery Analysis

Post-eruption vegetation recovery monitoring using Sentinel-2 multispectral timeseries. Per-pixel spectral index trajectories are constructed across a volcanic impact zone and partitioned by K-means clustering to identify spatially coherent recovery patterns.

## Study Area

La Palma, Canary Islands (Sentinel-2 tile T28RBS). The 2021 Cumbre Vieja eruption produced extensive lava flows across the western slopes of the island. Pre-eruption baseline imagery spans 2018 to 2019 (13 to 14 cloud-free acquisitions per year). Post-eruption analysis covers the eruption period and subsequent recovery phase.

## Spectral Indices

| Index | Sentinel-2 Bands | Sensitivity |
|-------|-----------------|-------------|
| NDVI  | B04, B08        | Photosynthetically active vegetation |
| SAVI  | B04, B08        | Vegetation in sparse or disturbed cover (L = 0.5) |
| NDWI  | B03, B08        | Surface water and moisture content |
| NBR   | B8A, B12        | Burn severity and char deposits (20 m) |

## Methods

**Band extraction.** `SentinelProcessor` parses Sentinel-2 `.SAFE` archives and copies image bands into a directory tree organized by tile and acquisition date (`data/processed/<tile>/<date>/`).

**Index calculation.** `RasterCalculator` converts surface reflectance bands to spectral indices. Named pixel windows (`lapalma`, `lavaflow_lapalma`) restrict computation to the study region.

**Timeseries construction.** `Timeseries` stacks index grids across all acquisition dates into a pixel-by-time matrix. Large negative inter-date differences (threshold -0.2), indicative of residual cloud or shadow contamination, are replaced by linear interpolation between neighbors.

**Clustering.** K-means (k = 5) partitions pixels by their full temporal trajectory, producing a raster where each cluster label represents a distinct recovery pattern.

**Trend estimation.** First-order polynomial fitting yields a per-pixel slope raster quantifying the rate and direction of vegetation change over the analysis period.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

## Data

Sentinel-2 Level-2A imagery is acquired programmatically from the [Copernicus Data Space Ecosystem](https://dataspace.copernicus.eu/) via `SentinelDownloader`. Register for a free account, then export credentials:

```bash
export CDSE_USERNAME=your.email@example.com
export CDSE_PASSWORD=your-password
```

Download and extract a date range for one tile:

```python
from src.data_processing import SentinelDownloader, SentinelProcessor

downloader = SentinelDownloader()
dates = downloader.fetch(
    tile='T28RBS',
    start_date='2021-09-01',
    end_date='2022-12-31',
    max_cloud_cover=30,
)
SentinelProcessor().process_all()
```

`fetch` returns the list of acquisition dates (8-digit strings, e.g. `'20211020'`) ready to pass to `Timeseries`. Archives land in `data/archive/` as `.zip`, are extracted to `data/raw/<product>.SAFE/`, and band extraction populates `data/processed/<tile>/<date>/`. All three steps are idempotent: re-running skips files already present.

The full La Palma dataset (pre-eruption baseline + eruption + first recovery year) can be acquired in one step:

```bash
uv run scripts/download_dataset.py
```

Expect roughly 25 to 40 GB of storage for a complete La Palma dataset (~50 acquisitions at 500 MB to 1 GB each).

## Usage

The CLI discovers available acquisition dates from `data/processed/<tile>/`, builds the timeseries, and writes the requested outputs to `results/analysis_results/`.

```bash
# default analysis: SAVI clustering over La Palma, full date range available
uv run main.py

# limit to the first post-eruption year and compute slopes alongside clusters
uv run main.py --start 2021-10-01 --end 2022-09-30 --slopes

# NDVI clustering over the lava flow with seven clusters
uv run main.py --bounds lavaflow_lapalma --index ndvi --clusters 7

# inspect which dates are locally available without running analysis
uv run main.py --list

# skip clustering, only produce the slope raster
uv run main.py --clusters 0 --slopes
```

| Flag | Default | Description |
|------|---------|-------------|
| `--tile` | `T28RBS` | Sentinel-2 tile ID |
| `--bounds` | `lapalma` | Named pixel window (`lapalma`, `lavaflow_lapalma`) |
| `--index` | `savi` | Spectral index: `ndvi`, `savi`, or `ndwi` |
| `--start`, `--end` | none | Inclusive date filters `YYYY-MM-DD` |
| `--clusters` | `5` | K-means cluster count, `0` to skip |
| `--slopes` | off | Also save per-pixel slope raster |
| `--list` | off | List discovered dates and exit |

## Structure

```
src/
  data_processing/    SentinelDownloader, SentinelProcessor, RasterCalculator, Timeseries, DEMProcessor
  helper/             RasterData dataclass, date lookup tables
  visualization/      Visualizer (matplotlib), 3D terrain rendering (PyVista)
scripts/              standalone diagnostic and analysis scripts
docs/research/        scientific background and eruption case study notes
```
