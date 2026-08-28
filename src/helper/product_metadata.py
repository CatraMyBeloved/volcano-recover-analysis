"""Read the reflectance scaling a Sentinel-2 L2A product was written with.

Digital numbers become surface reflectance as

    reflectance = (DN + BOA_ADD_OFFSET) / BOA_QUANTIFICATION_VALUE

From processing baseline 04.00 onward every L2A product carries
BOA_ADD_OFFSET = -1000, so dividing by 10000 alone overstates reflectance by
0.1 in every band. That error does not cancel in a normalised index: for NDVI
the numerator is a difference and survives, while the denominator gains 0.2, so
a true 0.75 reads as 0.50. Older products have no offset tag and need none.
"""
from functools import lru_cache
from pathlib import Path
from xml.etree import ElementTree

DEFAULT_QUANTIFICATION = 10000.0


@lru_cache(maxsize=None)
def reflectance_scaling(date_dir: str | Path) -> tuple[float, float]:
    """Return (offset, quantification) for the product in `date_dir`.

    Falls back to (0.0, 10000.0) when no manifest is present, which is correct
    for pre-04.00 baselines and the safest assumption otherwise.
    """
    manifest = Path(date_dir) / 'MTD_MSIL2A.xml'
    if not manifest.exists():
        return 0.0, DEFAULT_QUANTIFICATION

    root = ElementTree.parse(manifest).getroot()

    # The offset is per band but is identical across bands in every published
    # baseline, so the first entry is taken and represents all of them.
    offset = 0.0
    for element in root.iter('BOA_ADD_OFFSET'):
        if element.text:
            offset = float(element.text)
            break

    quantification = DEFAULT_QUANTIFICATION
    for element in root.iter('BOA_QUANTIFICATION_VALUE'):
        if element.text:
            quantification = float(element.text)
            break

    return offset, quantification


def crs_for_tile(tile: str) -> str:
    """EPSG code for a Sentinel-2 tile's UTM zone, as 'EPSG:32628'.

    The JP2 bands inside a SAFE archive carry no embedded CRS, so rasters
    derived from them come out with a valid transform and no projection, which
    makes them unusable as maps. The tile ID encodes the MGRS zone and latitude
    band, which is enough: bands C to M are south of the equator, N to X north.

    Raises ValueError on a tile ID that does not parse, rather than guessing.
    """
    name = tile[1:] if tile.upper().startswith('T') else tile
    if len(name) < 3 or not name[:2].isdigit():
        raise ValueError(f"Cannot read a UTM zone from tile ID '{tile}'")

    zone = int(name[:2])
    if not 1 <= zone <= 60:
        raise ValueError(f"UTM zone {zone} from tile ID '{tile}' is out of range")

    band = name[2].upper()
    if band < 'N':
        return f'EPSG:327{zone:02d}'
    return f'EPSG:326{zone:02d}'


def to_reflectance(data, date_dir: str | Path):
    """Convert digital numbers to surface reflectance, clipped to [0, 1]."""
    import numpy as np

    offset, quantification = reflectance_scaling(date_dir)
    return np.clip((data.astype('float32') + offset) / quantification, 0.0, 1.0)
