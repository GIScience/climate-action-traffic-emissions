from enum import Enum, StrEnum
from typing import Any, Dict, Tuple

import geopandas as gpd
import numpy as np
import pandas as pd
import pyproj
import rasterio
import shapely
import tqdm
from affine import Affine
from climatoology.base.artifact import ContinuousLegendData
from matplotlib import colors
from matplotlib.pyplot import colormaps
from pydantic_extra_types.color import Color
from rasterio.features import shapes
from rasterio.mask import mask
from rasterstats import gen_zonal_stats
from shapely import box
from shapely.geometry import mapping, shape

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


def calculate_pop_in_buffer(roads: gpd.GeoSeries, pop_raster: np.ndarray, pop_transform: Affine) -> list[float]:
    stats_10km = gen_zonal_stats(roads, pop_raster, affine=pop_transform, stats=['mean'], all_touched=True)
    result = [s['mean'] for s in tqdm.tqdm(stats_10km, total=len(roads))]
    return result


def get_pop_raster(target_geoms: gpd.GeoSeries, pop_raster_url: str) -> Tuple:
    bounds = box(*target_geoms.total_bounds)
    with rasterio.open(pop_raster_url) as src:
        clipped, src_transform = mask(src, [bounds], crop=True, all_touched=True, indexes=1)

    return clipped, src_transform


def get_built_up_raster(poly: shapely.MultiPolygon, built_raster_url: str) -> Dict[str, Any]:
    geom = mapping(poly)

    with rasterio.open(built_raster_url) as src:
        clipped, transform = mask(src, shapes=[geom], crop=True, all_touched=False, indexes=1)

        return {
            'array': clipped,
            'transform': transform,
            'crs': src.crs,
            'nodata': src.nodata,
        }


def get_built_up_geom(raster_dict: Dict[str, Any], traffic_gdf_crs: pyproj.CRS) -> gpd.GeoSeries:
    """
    Extracts built-up area vector geometries from built-up raster.
    :param raster_dict: Dict with array and meta information of built-up raster.
    :param traffic_gdf_crs: CRS of traffic_gdf.
    :return: GeoSeries with built-up areas.
    """
    arr = raster_dict['array']
    raster_crs = raster_dict['crs']
    transform = raster_dict['transform']
    nodata_value = raster_dict['nodata']

    mask = (~np.isnan(arr)) & (arr != nodata_value) & (arr != 0)

    built_up = gpd.GeoSeries(
        [shape(geom) for geom, _ in shapes(arr, mask=mask, transform=transform)],
        crs=raster_crs,
    )
    built_up = built_up.to_crs(traffic_gdf_crs)

    return built_up
