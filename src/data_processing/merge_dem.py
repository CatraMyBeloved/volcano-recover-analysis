import rasterio
import numpy as np
from pathlib import Path
from rasterio.merge import merge

def merge_dem_tiles(tile_paths, output_path):

    src_files = [rasterio.open(tile_path) for tile_path in tile_paths]

    mosaic, out_transform = merge(src_files)

    out_meta = src_files[0].meta.copy()

    out_meta.update({'height': mosaic.shape[1],
                     'width': mosaic.shape[2],
                    'transform': out_transform})

    with rasterio.open(output_path, 'w', **out_meta) as dst:
        dst.write(mosaic)

    for src in src_files:
        src.close()
