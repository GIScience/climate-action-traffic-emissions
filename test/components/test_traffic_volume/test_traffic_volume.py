import geopandas as gpd
import geopandas.testing
import numpy as np
import pandas as pd
import pytest
import shapely
from numpy.testing import assert_array_almost_equal
from shapely.geometry import LineString

from test.conftest import TEST_RESOURCES_DIR
from traffic_emissions.components.traffic_volume import (
    get_road_populations,
    get_roads,
    predict_traffic_volume,
    traffic_volume,
)

APPROVAL_FILES_DIR = TEST_RESOURCES_DIR / 'approved_files'

LINE_GEOM = gpd.GeoSeries(
    [LineString([(325193.9834442865, 4669724.10105637), (325111.5841199331, 4669734.855883078)]) for _ in range(6)]
)

DEFAULT_GEOM = gpd.GeoSeries([LineString([(10000, 9900), (10000, 10100)])])


@pytest.mark.parametrize('ohsome_fixture', (['ohsome_client_v1', 'ohsome_client_v2']))
@pytest.mark.vcr
def test_get_roads(ohsome_fixture, test_aoi, request):
    ohsome_client = request.getfixturevalue(ohsome_fixture)

    expected_df = pd.read_csv(
        APPROVAL_FILES_DIR / f'test_get_roads[{ohsome_fixture}].csv',
        dtype={'osm_id': str, 'lanes': int, 'maxspeed': str},
    )
    expected_df['geom'] = expected_df['geom'].apply(shapely.wkt.loads)
    expected_road_gdf = gpd.GeoDataFrame(expected_df, geometry='geom', crs=32643)

    test_time = '2025-10-01T12:00:00Z'
    road_gdf, total_length = get_roads(test_aoi, ohsome_client, target_timestamp=test_time)

    road_gdf['osm_id'] = road_gdf['osm_id'].astype(str)  # ohsome v2 returns an int

    gpd.testing.assert_geodataframe_equal(road_gdf, expected_road_gdf, check_dtype=False)
    assert int(total_length) == 83


def test_get_pop(default_aoi):
    road_gdf = gpd.GeoDataFrame(
        {},
        geometry=DEFAULT_GEOM,
        crs='EPSG:32632',
    )
    roads = get_road_populations(roads=road_gdf, pop_raster_url=TEST_RESOURCES_DIR / 'simple_raster.tif')
    assert_array_almost_equal(round(roads['pop_mean_10km'], 2), [2])


def test_predict_traffic_volume():
    road_gdf = gpd.GeoDataFrame(
        {
            'highway': ['motorway', 'trunk', 'primary', 'secondary'],
            'maxspeed': [130, 100, 'DE:urban', np.nan],
            'lanes': [3, 2, 2, np.nan],
        },
        geometry=LINE_GEOM,
    )
    road_gdf = road_gdf.rename_geometry('geom')

    df = pd.DataFrame(
        {
            'highway': ['motorway', 'trunk', 'primary', 'secondary'],
            'maxspeed': [130, 100, 'DE:urban', np.nan],
            'lanes': [3, 2, 2, np.nan],
            'mean_dtv': [15274.9, 14434.0, 6283.2, 3075.0],
        },
    )
    df.insert(3, 'geom', LINE_GEOM)
    expected = gpd.GeoDataFrame(df, geometry='geom')
    received = round(predict_traffic_volume(road_gdf), 1)
    pd.testing.assert_frame_equal(received, expected)


@pytest.mark.parametrize('ohsome_fixture', (['ohsome_client_v1', 'ohsome_client_v2']))
@pytest.mark.vcr
def test_traffic_volume(ohsome_fixture, small_aoi, request):
    ohsome_client = request.getfixturevalue(ohsome_fixture)

    # TODO: be more precise here - don't need to validate the ohsome geometries
    expected_df = pd.read_csv(
        APPROVAL_FILES_DIR / f'test_traffic_volume[{ohsome_fixture}].csv',
        dtype={'osm_id': str, 'maxspeed': str},
    )
    expected_df['geom'] = expected_df['geom'].apply(shapely.wkt.loads)
    expected_traffic_volume = gpd.GeoDataFrame(expected_df, geometry='geom', crs=32632)

    road_gdf = traffic_volume(aoi=small_aoi, ohsome=ohsome_client, pop_raster_url=TEST_RESOURCES_DIR / 'pop_raster.tif')
    road_gdf['osm_id'] = road_gdf['osm_id'].astype(str)
    geopandas.testing.assert_geodataframe_equal(road_gdf, expected_traffic_volume, check_dtype=False)
