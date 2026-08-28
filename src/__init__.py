"""Project package.

Importing this package repairs the PROJ database search path before rasterio is
loaded. It has to happen here, at the earliest import, because PROJ resolves its
search path once when GDAL initialises and ignores later changes to the
environment.

Why it is needed: a system-wide PROJ_LIB, typically left by a PostgreSQL or
PostGIS install, points PROJ at that installation's proj.db. GDAL honours the
variable over rasterio's own bundled database, and if the two are different
major versions every EPSG lookup fails with

    PROJ: proj_create_from_database: ... contains DATABASE.LAYOUT.VERSION.MINOR
    = 2 whereas a number >= 6 is expected. It comes from another PROJ
    installation.

which surfaces as "The EPSG code is unknown" and leaves written rasters with no
projection at all.
"""
import importlib.util
import os
from pathlib import Path


def _use_bundled_proj_data() -> Path | None:
    """Point PROJ at rasterio's bundled database, if one is present.

    Located through the import system rather than by importing rasterio, since
    importing it is what we have to get ahead of.
    """
    spec = importlib.util.find_spec('rasterio')
    if spec is None or spec.origin is None:
        return None

    bundled = Path(spec.origin).parent / 'proj_data'
    if not (bundled / 'proj.db').exists():
        return None

    # PROJ 9 reads PROJ_DATA; PROJ 6 to 8 read PROJ_LIB. Set both so the
    # override holds whichever version GDAL was linked against.
    os.environ['PROJ_DATA'] = str(bundled)
    os.environ['PROJ_LIB'] = str(bundled)
    return bundled


PROJ_DATA_DIR = _use_bundled_proj_data()
