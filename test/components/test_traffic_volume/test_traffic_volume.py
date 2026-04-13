import geopandas as gpd
import numpy as np
import pandas as pd
from approvaltests import verify
from numpy.testing import assert_array_almost_equal
from shapely.geometry import LineString
from vcr import use_cassette

from test.conftest import TEST_RESOURCES_DIR
from traffic_emissions.components.traffic_volume import (
    get_road_populations,
    get_roads,
    predict_traffic_volume,
    traffic_volume,
)

LINE_GEOM = gpd.GeoSeries(
    [LineString([(325193.9834442865, 4669724.10105637), (325111.5841199331, 4669734.855883078)]) for _ in range(6)]
)

DEFAULT_GEOM = gpd.GeoSeries([LineString([(477000, 5472000), (478000, 5473000)])])


@use_cassette('test/resources/vcr_cassettes/test_get_roads.yaml')
def test_get_roads(operator, road_test_aoi):
    road_gdf, total_length = get_roads(road_test_aoi, operator.ohsome)
    verify(road_gdf.to_csv())
    assert total_length == 83.0982247188029


def test_get_pop(default_aoi):
    road_gdf = gpd.GeoDataFrame(
        {},
        geometry=DEFAULT_GEOM,
        crs='EPSG:32632',
    )
    roads = get_road_populations(roads=road_gdf, pop_raster_url=TEST_RESOURCES_DIR / 'pop_raster.tif')
    assert_array_almost_equal(roads['pop_mean_10km'], [23.974042])


def test_predict_traffic_volume():
    road_gdf = gpd.GeoDataFrame(
        {
            'highway': ['motorway', 'trunk', 'primary', 'secondary'],
            'maxspeed': [130, 100, 'DE:urban', np.nan],
            'lanes': [3, 2, 2, np.nan],
        },
        geometry=LINE_GEOM,
    )
    df = pd.DataFrame(
        {
            'highway': ['motorway', 'trunk', 'primary', 'secondary'],
            'maxspeed': [130, 100, 'DE:urban', np.nan],
            'lanes': [3, 2, 2, np.nan],
            'mean_dtv': [15274.9, 14434.0, 6283.2, 3075.0],
        },
    )
    df.insert(3, 'geometry', LINE_GEOM)
    expected = gpd.GeoDataFrame(df, geometry='geometry')
    received = round(predict_traffic_volume(road_gdf), 1)
    pd.testing.assert_frame_equal(received, expected)


@use_cassette('test/resources/vcr_cassettes/test_traffic_volume.yaml')
def test_traffic_volume(operator, small_aoi):
    road_gdf = traffic_volume(
        aoi=small_aoi, ohsome=operator.ohsome, pop_raster_url=TEST_RESOURCES_DIR / 'pop_raster.tif'
    )
    verify(road_gdf.to_csv())
