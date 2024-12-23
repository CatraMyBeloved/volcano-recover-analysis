import rasterio
import numpy as np
from src.helper import *

def pixel_to_geographic(transform, coordinates):
    meters_per_pix_x = transform[0]
    meters_per_pix_y = transform[4]
    x_offset = transform[2]
    y_offset = transform[5]

    meters_x = coordinates[0]*meters_per_pix_x + x_offset
    meters_y = coordinates[1]*meters_per_pix_y + y_offset

    return meters_x, meters_y

def geographic_to_pixel(transform, coordinates):
    meters_per_pix_x = transform[0]
    meters_per_pix_y = transform[4]
    x_offset = transform[2]
    y_offset = transform[5]
    pixels_x = (coordinates[0] - x_offset) / meters_per_pix_x
    pixels_y = (coordinates[1] - y_offset) / meters_per_pix_y

    return pixels_x, pixels_y