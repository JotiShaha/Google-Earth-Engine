# !pip install --upgrade xee
# !pip install --U geemap
# !pip install --upgrade xarray
# !pip install earthengine-api xee xarray rasterio shapely

# Import Libraries
import ee
import geemap
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import xee
import shapely.geometry
from xee import helpers

ee.Authenticate()
ee.Initialize(
    project = '---google earth engine project info---',
    opt_url = 'https://earthengine-highvolume.googleapis.com'
)

# Create Interactive map
climate_map = geemap.Map(basemap = 'SATELLITE')
climate_map

# Extract the study area
study_area = climate_map.draw_last_feature.geometry()
study_area

# Extract administrative boundary
country_boundary = (
    ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
    .filter(ee.Filter.eq('country_na', 'Bangladesh'))
    .geometry()
    .simplify(100)
)

# Add boundary layer to map
climate_map.addLayer(country_boundary, {}, 'Bangladesh')

# Load GPM dataset monthly precipitation
gpm_monthly = (
    ee.ImageCollection("NASA/GPM_L3/IMERG_MONTHLY_V07")
    .filterDate('2015-01-01', '2026-01-01')
    .select('precipitation')
    .map(
        lambda image: (
            image.clip(country_boundary)
            .copyProperties(image, ['system:time_start'])
        )
    )
)
gpm_monthly

# Convert your Earth Engine geometry to a Shapely geometry for the new xee API
aoi_geojson = country_boundary.getInfo()
aoi = shapely.geometry.shape(aoi_geojson)

# Generate the exact grid parameters using xee.helpers
grid_params = helpers.fit_geometry(
    geometry=aoi,
    geometry_crs='EPSG:4326',
    grid_crs='EPSG:4326',
    grid_scale=(0.1, -0.1)  # 0.1 degree resolution (negative Y for north-up)
)

# Convert Earth Engine Collection to Xarray Dataset using the grid_params
xr_precip = xr.open_dataset(
    gpm_monthly,
    engine='ee',
    **grid_params
)

# sorting and unit conversion
xr_precip = xr_precip.sortby('time') * 730.5 # 365.5/12*24 for yearly 

print(xr_precip)

# Calculate annual precipitation totals
annual_precip = xr_precip.resample(time= 'YE').sum('time') # YE = YEAR

# Replace zero values with NaN, NaN = No data
annual_precip = xr.where(
    annual_precip == 0,
    np.nan,
    annual_precip
)

# Visualize annual rainfall map
plot = annual_precip.precipitation.plot.contourf(
    x= 'x',
    y= 'y',
    col= 'time',
    col_wrap = 5,
    robust = True,
    cmap = 'Blues',
    figsize= (16, 10),
    cbar_kwargs= {'label': 'Precipitation (mm)',
                  'shrink': 0.9,
                  'pad': 0.05}
)

  # Grab the list of years directly from the dataset
years = annual_precip.time.dt.year.values

# Loop through the maps and the years at the exact same time using zip()
for ax, year in zip(plot.axes.flat, years):
  ax.set_title(f'Annual Precipitation {year}', fontsize=12)
  #ax.set_title(ax.get_title().replace('time', 'Time'), fontsize=15)
  #ax.set_xlabel('Longitude', fontsize=15)
  #ax.set_ylabel('Latitude', fontsize=15)
  ax.tick_params(axis= 'both',labelsize=10)

# # Customize colorbar label font size and tick label size
plot.cbar.ax.set_label('Precipitation (mm)', fontsize=15)
plot.cbar.ax.tick_params(labelsize=15)

plot.fig.tight_layout()
plt.show()
plt.savefig('Annual_average_precipitation.png',
            bbox_inches = 'tight',
            dpi = 360)
plt.show()

# Compute interannual rainfall map
precip_change = annual_precip.diff('time')

# For year i, result= annual_precip[i+1] - annual_precip[i]

plot = precip_change.precipitation.plot.contourf(
    x= 'x',
    y= 'y',
    col= 'time',
    col_wrap= 5,
    robust= True,
    cmap= 'RdBu',
    figsize= (22, 10),
    cbar_kwargs= {'label': 'Precipitation Change (mm)',
                   'shrink': 0.9,
                   'pad': 0.05}
)

## Loop through all the generated subplots
for ax in plot.axes.flat:
    old_title = ax.get_title()
    if 'time' in old_title:
        year = old_title.split('=')[-1].strip()[:4]
        ax.set_title(f'Annual Precipitation Change {year}', fontsize=12, fontweight='bold')

   #ax.set_xlabel('Longitude', fontsize=15)
   #ax.set_ylabel('Latitude', fontsize=15)
    ax.tick_params(axis='both', labelsize=12)

# Customize colorbar
plot.cbar.ax.set_ylabel('Precipitation Change (mm)', fontsize=15)
plot.cbar.ax.tick_params(labelsize=15)

# plot.fig.subplots_adjust(
#    right=0.85, 
#    hspace=0.3, 
#    wspace=0.15)

plt.savefig('Annual_change_precipitation.png', 
            bbox_inches='tight', 
            dpi=300)
plt.show()

# Calculate Average annual change
average_change = precip_change.mean(dim= 'time')
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(5, 5))

plot = average_change.precipitation.plot.contourf(
    x= 'x',
    y= 'y',
    robust= True,
    cmap= 'coolwarm',
    levels= 12,
    cbar_kwargs= {'label': 'Precipitation Change (mm)',
                   'shrink': 0.9,
                   'pad': 0.05},
    ax=ax 
)

ax.set_title('Average Precipitation Change', fontsize=12, fontweight='bold')
ax.tick_params(axis= 'both',labelsize=12)
ax.set_xlabel('Longitude', fontsize=12)
ax.set_ylabel('Latitude', fontsize=12)


# North Arrow (upper right)
ax.annotate(
    'N',
    xy=(0.95, 0.95),
    xytext=(0.95, 0.85),
    arrowprops=dict(facecolor='black', width=2, headwidth=5),
    ha='center',
    va='center',
    fontsize=16,
    xycoords=ax.transAxes
)

plt.show()
# Save image as png
plt.savefig('Average_precipitation_change_.png', 
            bbox_inches='tight', 
            dpi=300)
