import pandas as pd
import pyproj
import rasterio
from climatoology.base.artifact import ContinuousLegendData
from pydantic_extra_types.color import Color
from shapely import wkt

from traffic_emissions.components.utils import (
    get_built_up_geom,
    get_built_up_raster,
    get_colors_legend,
)


def test_get_colors_legend():
    expected_colors = pd.Series([Color('#ffc'), Color('#fb4b29'), Color('#800026')])
    expected_legend = ContinuousLegendData(
        cmap_name='YlOrRd',
        ticks={'1.5': 0.0, '2': 0.25, '2.6': 0.5, '3.4': 0.75, '4.5': 1.0},
    )
    colors, legend = get_colors_legend(pd.Series([1.5, 3.0, 4.5]))

    assert colors == expected_colors.to_list()
    assert legend.cmap_name == expected_legend.cmap_name
    assert {k: round(v, 2) for k, v in legend.ticks.items()} == expected_legend.ticks


def test_get_built_up_geom():
    with rasterio.open('test/resources/built_up_raster.tif') as src:
        raster_dict = {
            'array': src.read(1),
            'transform': src.transform,
            'crs': src.crs,
            'nodata': src.nodata,
        }
    df = pd.read_csv('test/resources/built_up.csv')
    geom = wkt.loads(df['geometry'].iloc[0])
    received = get_built_up_geom(raster_dict=raster_dict, traffic_gdf_crs=pyproj.CRS('EPSG:32632'))
    assert received == geom


def test_get_built_up_raster(default_aoi, mock_s3_built_up_raster):
    raster_dict = get_built_up_raster(default_aoi, mock_s3_built_up_raster)
    assert raster_dict['array'].ndim == 2
    assert raster_dict['array'].size > 0
    assert raster_dict['array'][1][0] == 1882
    assert raster_dict['crs'] == pyproj.CRS('EPSG:4326')
    assert raster_dict['nodata'] == 0.0
