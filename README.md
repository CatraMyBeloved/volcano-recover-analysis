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

**Reflectance conversion.** Digital numbers become reflectance as `(DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE`, read per product from its own manifest. From processing baseline 04.00 the offset is -1000, and ignoring it compresses every normalised index toward zero by a factor that depends on surface brightness, hitting dark surfaces such as fresh lava hardest.

**Cloud masking.** The product scene classification layer (`SCL`) marks cloud, cirrus, cloud shadow, snow, saturation and nodata per pixel and per date; those pixels become NaN. They are never interpolated: an interpolated value cannot be told apart from a measurement downstream, and any threshold on index change cannot tell contamination from a real event, so on this dataset the previous heuristic interpolated across the eruption itself.

**Compositing.** `Compositor` takes a per-pixel median over the clear observations in a period. Cloud on a single date is common here but moves between dates, so nearly every pixel has several clear looks across a season even when no single scene is clear. Every composite ships a count raster recording how many observations stand behind each pixel.

**Timeseries construction.** `Timeseries` stacks masked index grids across acquisition dates into a pixel-by-time matrix, with unmeasurable pixels left as NaN.

**Clustering.** `Compositor.cluster_periods` partitions pixels by their per-period composite values, labelling clusters in ascending order of the first period so a label means the same thing between runs. Clustering the raw date-by-date trajectory does not work on a dataset of a few seasonal windows: the dates arrive in near-simultaneous clumps separated by years, and no pixel is clear on every date, so K-means has nothing complete to work with.

**Trend estimation.** A per-pixel least-squares line against decimal years, solved over each pixel's own clear observations, yields a slope raster in index units per year. Fitting against position in the date list would treat a three-year gap as one step.

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

Expect roughly 500 MB to 1 GB per acquisition, so about 13 GB of archives for the 20-scene focused set and a similar amount again once extracted.

Only orbit R023 images La Palma within tile T28RBS; R123 scenes clip a corner of the tile well away from the island and cover under a tenth of it while still being large, valid and low-cloud products. `SentinelDownloader` filters on the footprint the catalogue returns, before ranking by cloud, because cloud cover is assessed over valid pixels and so a scene that barely touches the island reports near-zero cloud and wins any ranking by clearness.

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
| `--clusters` | `5` | K-means cluster count, `0` to skip. Requires a pixel to be clear on every date, which a set of seasonal windows will not satisfy; use `scripts/build_composites.py --clusters 5` instead |
| `--slopes` | off | Also save per-pixel slope raster |
| `--list` | off | List discovered dates and exit |

## Structure

```
src/
  __init__.py         repairs the PROJ search path before rasterio loads
  data_processing/    SentinelDownloader, SentinelProcessor, RasterCalculator,
                      Compositor, Timeseries, DEMProcessor
  helper/             RasterData dataclass, reflectance scaling and tile CRS,
                      date lookup tables
  visualization/      Visualizer (matplotlib), 3D terrain rendering (PyVista)
scripts/              standalone diagnostic and analysis scripts
docs/research/        scientific background and eruption case study notes
```

Scripts, in the order they are usually run:

| Script | Purpose |
|--------|---------|
| `survey_windows.py` | list candidate scenes per period with cloud and island coverage, downloading nothing |
| `download_dataset.py` | fetch the clearest covering scenes per period, extract and process them |
| `verify_coverage.py` | read the pixels and report valid, usable and clear-observation depth per scene |
| `build_composites.py` | per-period median composites, count rasters, clusters and a provenance record |
| `plot_diagnostics.py` | inspection figures for composites, change maps, clusters and distributions |

`src/__init__.py` exists because a system-wide `PROJ_LIB`, typically left by a
PostgreSQL or PostGIS install, points PROJ at that installation's `proj.db`.
GDAL honours it over rasterio's bundled copy, and if the two are different major
versions every EPSG lookup fails and rasters are written with no projection. The
override has to happen before rasterio is first imported, because PROJ resolves
its search path once at GDAL initialisation.
