using Pkg
Pkg.add([
    "GeoData",        # High-level array interface for geo data
    "ArchGDAL",       # For reading various geodata formats
    "Statistics",     # For mean, std calculations
    "DiskArrays",     # For out-of-memory processing
    "Dates"          # For handling temporal data
])

using GeoData
using ArchGDAL
using Statistics
using DiskArrays
using Dates

function read_raster(tile, capture_date, res="10m", filename)
    filepath = string("../../data/processed/$tile/$capture_date/$res/$filename")
    dataset = ArchGDAL.read_raster(filepath)

    data_array = dataset[1]
    return data_array
end

