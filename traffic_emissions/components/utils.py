from enum import Enum, StrEnum

import pandas as pd
from climatoology.base.artifact import ContinuousLegendData
from matplotlib import colors
from matplotlib.pyplot import colormaps
from pydantic_extra_types.color import Color

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


def get_colors_legend(legend_upper_cap: int, color_series: pd.Series) -> tuple[pd.Series, ContinuousLegendData]:
    norm = colors.Normalize(vmin=0, vmax=legend_upper_cap)
    cmap = colormaps.get('YlOrRd')
    cmap.set_under('#808080')
    color = color_series.apply(lambda v: Color(colors.to_hex(cmap(norm(v)))))
    legend = ContinuousLegendData(
        cmap_name='YlOrRd',
        ticks={f'> {legend_upper_cap}': 1, '0': 0},
    )
    return color, legend
