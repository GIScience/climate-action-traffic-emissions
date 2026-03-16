import geopandas as gpd
import pandas as pd
import pyproj
from climatoology.base.artifact import ContinuousLegendData
from pydantic_extra_types.color import Color
from shapely import wkt

from test.components.test_traffic_volume.test_traffic_volume import DEFAULT_GEOM
from traffic_emissions.components.utils import calculate_pop_in_buffer, get_built_up_geom, get_colors_legend


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


def test_calculate_pop_in_buffer():
    road_gdf = gpd.GeoDataFrame(
        {},
        geometry=DEFAULT_GEOM,
        crs='EPSG:32632',
    )
    expected = pd.Series([2.15584], name='pop_mean_10km')
    received = calculate_pop_in_buffer(road_gdf, 'test/resources/pop_raster.tif')
    pd.testing.assert_series_equal(received['pop_mean_10km'].round(5), expected)


def test_get_built_up_geom():
    df = pd.read_csv('test/resources/built_up.csv')
    geom = wkt.loads(df['geometry'].iloc[0])
    received = get_built_up_geom('test/resources/built_up_raster.tif', pyproj.CRS('EPSG:32632'))
    assert received == geom
