from enum import Enum, StrEnum

import ee
import geemap
import numpy as np
import pandas as pd
import pyproj
import rasterio
import shapely
from climatoology.base.artifact import ContinuousLegendData
from matplotlib import colors
from matplotlib.pyplot import colormaps
from pydantic_extra_types.color import Color
from pyproj import Transformer
from rasterio.features import shapes
from rasterio.mask import mask
from shapely import MultiPolygon
from shapely.geometry import shape
from shapely.ops import unary_union

# To recalculate these numbers, run the plugin for Berlin
POP_DENS_BERLIN = 41  # Population density 2025 in Berlin per 100 m grid cell (from GHS-POP)
ROAD_LENGTH_PER_CAPITA_BERLIN = 2.1  # Road length per capita in Berlin in meters

GHSL_PROJ_YEAR = 'P2023A'
GHSL_EPOCH = '2025'
RASTER_SCALE = 100

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


def calculate_mean_pop_density_polygon(polygon: shapely.MultiPolygon, raster_path: str) -> tuple[float, float]:
    """
    Calculates mean and total population in the given polygons using the GHS_POP population raster.

    :param polygon: Polygon of AOI for which population density is calculated (EPSG: 4326)
    :param raster_path: Path to population raster
    :return: mean_value: mean population per grid cell in the given polygons
    :return: sum_value: total population in the given polygons
    """
    with rasterio.open(raster_path) as src:
        out_image, _ = mask(src, [polygon], crop=True, nodata=np.nan)
        valid_data = out_image[~np.isnan(out_image)]
        if valid_data.size == 0:
            raise ValueError(f'No valid population data found in {raster_path} for the given area of interest.')

        mean_value = valid_data.mean()
        sum_value = valid_data.sum()
        return mean_value, sum_value


def get_pop_raster(aoi: shapely.MultiPolygon, pop_path: str) -> None:
    geom = ee.Geometry(shapely.geometry.mapping(aoi))
    ghsl = ee.Image(f'JRC/GHSL/{GHSL_PROJ_YEAR}/GHS_POP/{GHSL_EPOCH}')
    clipped = ghsl.clip(geom).reproject('EPSG:4326', None, RASTER_SCALE)
    geemap.ee_export_image(clipped, filename=pop_path, scale=RASTER_SCALE, file_per_band=False)


def get_built_up_raster(aoi: shapely.MultiPolygon, built_up_path: str) -> None:
    """
    Gets raster showing built-up surfaces, expressed in square metres per 100 m grid cell, in the AOI.
    """
    geom = ee.Geometry(shapely.geometry.mapping(aoi))
    ghsl = ee.Image(f'JRC/GHSL/{GHSL_PROJ_YEAR}/GHS_BUILT_S/{GHSL_EPOCH}').select(['built_surface'])
    clipped = ghsl.clip(geom).reproject('EPSG:4326', None, RASTER_SCALE)
    geemap.ee_export_image(clipped, filename=built_up_path, scale=RASTER_SCALE, file_per_band=False)


def get_built_up_geom(raster_path: str, traffic_gdf_crs: pyproj.CRS) -> shapely.MultiPolygon:
    """
    Extracts built-up area vector geometries from built-up raster.
    :param raster_path: Filepath of built-up raster.
    :param traffic_gdf_crs: CRS of traffic_gdf.
    :return: GeoSeries with built-up areas as multipolygon.
    """
    with rasterio.open(raster_path) as src:
        arr = src.read(1)
        raster_crs = src.crs
        transform = src.transform
        nodata_value = src.nodata

    mask = (~np.isnan(arr)) & (arr != nodata_value) & (arr != 0)
    geoms = []
    for geom, _ in shapes(arr, mask=mask, transform=transform):
        geoms.append(shape(geom))

    multipolygon: MultiPolygon = unary_union(geoms)
    transformer = Transformer.from_crs(raster_crs, traffic_gdf_crs, always_xy=True)
    multipolygon_proj = shapely.transform(multipolygon, transformer.transform, interleaved=False)

    return multipolygon_proj
