from enum import Enum, StrEnum

import numpy as np
import pandas as pd
import rasterio
import shapely
from climatoology.base.artifact import ContinuousLegendData
from matplotlib import colors
from matplotlib.pyplot import colormaps
from pydantic_extra_types.color import Color
from rasterio.mask import mask

POP_DENS_BERLIN = 1367  # Population density 2025 in Berlin bounding box per 30 arc second grid cell (from GHS-POP)
ROAD_LENGTH_PER_CAPITA_BERLIN = 2.1  # Road length per capita in Berlin in meters

MARKET_SHARES = {
    'petrol_car': 0.534,
    'diesel_car': 0.25,
    'motorcycle': 0.082,
    'bus': 0.001,
    'rigid_truck': 0.062,
    'articulated_truck': 0.004,
    'other': 0.042,
}


class VehicleType(Enum):
    CAR = 'car'
    MOTORCYCLE = 'motorcycle'
    RIGID_TRUCK = 'rigid_truck'
    ARTICULATED_TRUCK = 'articulated_truck'
    BUS = 'bus'


class Topic(StrEnum):
    MAPS = 'Emission maps'
    CHARTS = 'Emission charts'


DENSITY_PETROL = 720
DENSITY_DIESEL = 820


def get_colors_legend(color_series: pd.Series) -> tuple[list[Color], ContinuousLegendData]:
    norm = colors.LogNorm(vmin=color_series.min(), vmax=color_series.max())
    cmap = colormaps.get('YlOrRd')
    cmap.set_under('#808080')
    color = [Color(colors.to_hex(col)) for col in cmap(norm(color_series))]

    tick_values = np.logspace(np.log10(color_series.min()), np.log10(color_series.max()), num=5)
    if color_series.min() < 10:
        ticks = {f'{round(v, 1):n}': norm(v) for v in tick_values}
    else:
        ticks = {f'{round(v):n}': norm(v) for v in tick_values}

    legend = ContinuousLegendData(
        cmap_name='YlOrRd',
        ticks=ticks,
    )
    return color, legend


def calculate_mean_pop_density_polygon(polygon: shapely.MultiPolygon) -> tuple[float, float]:
    """
    Calculates mean and total population in the given polygons using the GHS_POP population raster.

    :param polygon: Polygon of AOI for which population density is calculated (EPSG: 4326)
    :return: mean_value: mean population per grid cell in the given polygons
    :return: sum_value: total population in the given polygons
    """
    raster_path = 'resources/pop_dens.tif'
    with rasterio.open(raster_path) as src:
        out_image, _ = mask(src, [polygon], crop=True, nodata=np.nan)
        valid_data = out_image[~np.isnan(out_image)]
        if valid_data.size == 0:
            raise ValueError(f'No valid population data found in {raster_path} for the given area of interest.')

        mean_value = valid_data.mean()
        sum_value = valid_data.sum()
        return mean_value, sum_value
