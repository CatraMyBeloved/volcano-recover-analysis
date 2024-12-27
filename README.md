# Volcanic Recovery Analysis Project

## Project Overview
Analysis of vegetation recovery patterns following volcanic eruptions using satellite imagery and NDVI analysis.

## Project Goals
- Track vegetation recovery after volcanic eruptions
- Map lava flow extent using vegetation analysis
- Compare recovery patterns in different impact zones
- Document recovery processes using satellite data

## Project Status
Currently working on the different tools needed:
 - [x] raster processing
 - [x] index calculations
 - [x] data selection
 - [x] data processing over longer time frame
 - [x] simple visualizations
 - [x] DEM management and visualization
 
## Repository Structure

### /data (not tracked in git)
- /raw - Original satellite imagery
- /archive - Original .zips
- /processed - Processed data
- /DEM_raw - Raw dem data
- /DEM_finished - Reprojected DEM files
- /DEM_merged - Merged DEM files
 - Note: Current DEM management is currently being reworked and will be depreciated

### /docs
- /research - Research notes
- /methods - Analysis methods

### /qgis
- qgis files (duh)
### /src
- /data_processing - Data processing scripts
- /helper - Helper functions 
- /julia - TODO: add julia code for optimized calculations
- /visualization - Data visualization

### /results
- /figures - Generated figures
- /maps - Generated maps
- /analysis_results - Results of timeline analysis
- /rasters - Generate raster data, such as calculated indexes
## Setup Instructions
[To be added]

## Current Focus
Development of general tools to examine other volcanic eruptions
