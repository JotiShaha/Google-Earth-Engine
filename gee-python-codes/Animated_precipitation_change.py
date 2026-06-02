#Install libraries
!pip install xee
!pip install geemap
!pip install --upgrade xee
!pip install --U geemap

#Import libraries
import ee
import geemap
import xee
import xarray as xr
import numpy as np
import geopandas as gpd
import matplotlib.pyplot as plt


# GEE authenticate with colab python
ee.Authenticate()
ee.Initialize(
    project= #'project_name', # earth engine project inforamtion, project name
    opt_url = 'https://earthengine-highvolume.googleapis.com'
)

#Create interactive map 
satellite_map = geemap.Map(basemap='SATELLITE')
satellite_map

# select study area
study_area = satellite_map.draw_last_feature.geometry()
study_area

# Loading administrative boundary
country_boun = (
    ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
    .filterBounds(study_area)
    .geometry()
    .simplify(100)
)

satellite_map.addLayer(country_boun, {}, 'Bangladesh', False)
satellite_map.centerObject(country_boun,8)

# Load monthly GPM data
gpm_precip = (
    ee.ImageCollection("NASA/GPM_L3/IMERG_MONTHLY_V07")
    .filterDate('2000-01-01','2025-12-31')
    .select('precipitation')
    .map(
        lambda img:(
            img.clip(country_boun)
            .copyProperties(img, ['system:time_start']
        )
    )
)
)

# Converting monthly to annual total precipitation
gpm_year_sequence = ee.List.sequence(2000, 2025)
def annual_precip(year):
    start = ee.Date.fromYMD(year,1,1)
    end = start.advance(1, 'year')

    annual_total = (
        gpm_precip
        .filterDate(start, end)
        .sum()
        .multiply(730) # Hourly milimeter precipitation to yearly milimeter precipitation, 365/12*24 = 730 
        .rename('Annual Precipitation')
        .set(
            'year_label',
            ee.Number(year).format()
             )
        .set('system:time_start',start.milis())
    )
    return annual_precip

annual_precip_collection = ee.ImageCollection(
    gpm_year_sequence.map(annual_precip)
)


# Calculate Interannual precipitation change
annual_list = annual_precip_collection.toList(annual_precip_collection.size())

def yearly_difference(index):
    current_img = ee.Image(annual_list.get(index))
    previous_img = ee.Image(annual_list.get(ee.Number(index).substract(1)))

    precip_change =(
        current_img.substract(previous_img)
        .rename('Precipitation Change')
        .set('year_label', current_img.get('year_label'))
        .set('system:time_start', current_img.get('system:time_start'))
    )
    return precip_change
change_collection = ee.ImageCollection(
    ee.List.sequence(1, annual_precip_collection.size().substract(1))
    .map(yearly_difference)
)

"""
Precipitation change detection animation by Graphics Interchange Format (GIF).
Visualization on the colab environment for animating precipation change detection.

"""
# Visualization parameters
change_vis ={
    'min':-500,
    'max':'500',
    'palette': ['darkred','red','orange','white','lightblue','blue','darkblue']
}

# Overlook by adding sample layer to map
sample_change = ee.Image(change_collection.first())

satellite_map.addLayer(sample_change, change_vis, 'Precipitation Change overlook')
satellite_map

# Creating animated GIF
gif_parameter = {
    'region': country_boun,
    'dimension': 1000,
    'framesPerSecond':2,
    'crs': 'EPSG:4326',
    'min': -500,
    'max': 500,
    'palette': ['darkred','red','orange','white','lightblue','blue','darkblue']
}

gif_link = change_collection.getVideoThumbURL(gif_parameter)
print("Animated GIF URL")
print(gif_link)

geemap.show_image(gif_link) # For displaying animation in the Google Colab