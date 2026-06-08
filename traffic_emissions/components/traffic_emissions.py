import logging
from enum import Enum
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pyproj
import shapely
from climatoology.base.artifact import Artifact, ArtifactMetadata, Legend
from climatoology.base.artifact_creators import create_plotly_chart_artifact, create_vector_artifact
from climatoology.base.baseoperator import AoiProperties
from climatoology.base.computation import ComputationResources
from geopandas import GeoDataFrame
from pandas import Index
from shapely import MultiPolygon

from traffic_emissions.components.utils import (
    DENSITY_DIESEL,
    DENSITY_PETROL,
    MARKET_SHARES,
    Topic,
    VehicleType,
    get_built_up_geom,
    get_built_up_raster,
    get_colors_legend,
)

log = logging.getLogger(__name__)


class EmissionsFactors(Enum):
    CO2 = {  # dead: disable
        'name': 'CO2',
        'column': 't_CO2_km_yr',
        'fuel': 2389,
        'motorway': 204,
        'inside': 197,
        'outside': 154,
        'display_name': 'CO₂',
    }
    CO = {  # dead: disable
        'name': 'CO',
        'column': 't_CO_km_yr',
        'fuel': 39.4,
        'motorway': 3.36,
        'inside': 3.25,
        'outside': 2.54,
        'display_name': 'CO',
    }
    NOx = {  # dead: disable
        'name': 'NOx',
        'column': 't_NOx_km_yr',
        'fuel': 6.3,
        'motorway': 0.54,
        'inside': 0.52,
        'outside': 0.41,
        'display_name': 'NOₓ',
    }


UNITS = {
    'KM': {
        'column': 'km_yr',
        'unit': 't/road-km',
    },
    'KM2': {
        'column': 'km2_yr',
        'unit': 't/km²',
    },
}


def traffic_emissions(
    road_gdf: gpd.GeoDataFrame, aoi_poly: shapely.MultiPolygon, built_raster_url: str
) -> gpd.GeoDataFrame:
    """
    Calculates annual road traffic emissions [t/road-km] for each road segment.

    :return: GeoDataFrame of emissions [t/road-km] for each road segment. Contains the following columns: geometry, highway, lanes, maxspeed, mean_dtv (mean daily traffic volume), road_type (inside city/outside city/motorway), t_CO2_km_yr, t_CO_km_yr, t_NOx_km_yr
    """
    log.info('Calculating annual traffic emissions')
    traffic_gdf = preprocess(road_gdf, aoi_poly, built_raster_url=built_raster_url)
    emissions_gdf = calculate_emissions(traffic_gdf)
    return emissions_gdf


def get_emission_sums(emissions_gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict]:
    emissions_gdf_with_yearly_emissions = emissions_gdf.copy()
    emissions_gdf_with_yearly_emissions['length'] = emissions_gdf_with_yearly_emissions.geometry.length
    emissions_gdf_with_yearly_emissions['t_CO2_yr'] = emissions_gdf_with_yearly_emissions['t_CO2_km_yr'] * (
        emissions_gdf_with_yearly_emissions['length'] / 1000
    )
    emissions_gdf_with_yearly_emissions['t_CO_yr'] = emissions_gdf_with_yearly_emissions['t_CO_km_yr'] * (
        emissions_gdf_with_yearly_emissions['length'] / 1000
    )
    emissions_gdf_with_yearly_emissions['t_NOx_yr'] = emissions_gdf_with_yearly_emissions['t_NOx_km_yr'] * (
        emissions_gdf_with_yearly_emissions['length'] / 1000
    )
    emission_sums = {
        'CO2': emissions_gdf_with_yearly_emissions['t_CO2_yr'].sum() / 1000,
        'CO': emissions_gdf_with_yearly_emissions['t_CO_yr'].sum() / 1000,
        'NOx': emissions_gdf_with_yearly_emissions['t_NOx_yr'].sum() / 1000,
    }
    return emissions_gdf_with_yearly_emissions, emission_sums


def preprocess(
    gdf_traffic: gpd.GeoDataFrame, aoi_poly: shapely.MultiPolygon, built_raster_url: str
) -> gpd.GeoDataFrame:
    """
    Preprocesses gdf_traffic for emission calculation.

    :param built_raster_url: URL of the built-up raster in the S3 storage
    :param aoi_poly: AOI boundary as shapely.MultiPolygon
    :param gdf_traffic: GeoDataFrame of OSM road network with estimated traffic volumes
    :return: gdf_traffic: GeoDataFrame with roads and their attributes (inside city / outside city / motorway)
    """
    gdf_traffic['road_type'] = 'outside'

    roads_in_cities_idx = roads_intersecting_cities(
        aoi_poly=aoi_poly, roads=gdf_traffic, built_raster_url=built_raster_url
    )
    gdf_traffic.loc[roads_in_cities_idx, 'road_type'] = 'inside'

    motorway_idx = gdf_traffic['highway'].isin(['motorway', 'motorway_link'])
    gdf_traffic.loc[
        motorway_idx,
        'road_type',
    ] = 'motorway'

    gdf_traffic.maxspeed = pd.to_numeric(gdf_traffic.maxspeed, errors='coerce').astype('Int64')

    return gdf_traffic


def roads_intersecting_cities(aoi_poly: MultiPolygon, built_raster_url: str, roads: GeoDataFrame) -> Index:
    built_up = get_built_up_area(aoi_poly=aoi_poly, traffic_gdf_crs=roads.crs, built_raster_url=built_raster_url)

    intersections = roads.sindex.query(built_up, predicate='intersects')
    roads_in_cities_idx = roads.index[np.unique(intersections[1])]

    return roads_in_cities_idx


def get_built_up_area(
    aoi_poly: shapely.MultiPolygon, traffic_gdf_crs: pyproj.CRS, built_raster_url: str
) -> gpd.GeoSeries:
    """
    Gets built-up areas in the AOI as a GeoSeries.
    :param built_raster_url: URL of the built-up raster in the S3 storage
    :param aoi_poly: Area of interest as multipolygon.
    :param traffic_gdf_crs: CRS of traffic_gdf.
    :return: GeoSeries with built-up areas.
    """
    raster_dict = get_built_up_raster(aoi_poly, built_raster_url=built_raster_url)
    built_up = get_built_up_geom(raster_dict, traffic_gdf_crs)

    return built_up


def calculate_emissions(gdf_traffic: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Calculates CO2, CO, and NOx emissions [g per day] of each road segment.

    :param gdf_traffic: GeoDataFrame with roads and their attributes (inside city / outside city / motorway)
    :return: traffic_gdf: GeoDataFrame with road segments and their CO2, CO, and NOx emissions [t per road-km per year]
    """
    for emission_type in EmissionsFactors:
        get_single_emission(gdf_traffic, emission=emission_type)

    return gdf_traffic


def get_single_emission(gdf_traffic: gpd.GeoDataFrame, emission: EmissionsFactors) -> None:
    column_name = emission.value.get('column')
    gdf_traffic[column_name] = gdf_traffic.apply(
        estimate_ghg,
        axis=1,
        emission_factors=emission.value,
    )
    gdf_traffic[column_name] = gdf_traffic[column_name].apply(lambda x: np.nan if x is None or len(str(x)) == 0 else x)


def estimate_ghg(row: gpd.GeoSeries, emission_factors: dict) -> float:
    """
    Calculates annual emissions of the OSM road segment [t per road-km].

    :param row: OSM road segment
    :param emission_factors: Emission factors for fuel consumption, motorways, inside city, and outside city [g per vehicle-km]
    :return: Emissions of the road segment [t per road-km per year]
    """
    count_vehicles = row['mean_dtv']
    road_type = row['road_type']
    speed = row['maxspeed']

    if not pd.isna(speed) and speed > 0:
        fuel = dict()
        for vehicle in VehicleType:
            fuel.update({vehicle: get_fuel_consumption(vehicle, speed)})

        # weight fuel consumption by market shares of vehicle types
        fuel_consumption = (
            fuel[VehicleType.CAR] * MARKET_SHARES['petrol_car']
            + fuel[VehicleType.CAR] * MARKET_SHARES['diesel_car']
            + fuel[VehicleType.MOTORCYCLE] * MARKET_SHARES['motorcycle']
            + fuel[VehicleType.BUS] * MARKET_SHARES['bus']
            + fuel[VehicleType.RIGID_TRUCK] * MARKET_SHARES['rigid_truck']
            + fuel[VehicleType.ARTICULATED_TRUCK] * MARKET_SHARES['articulated_truck']
            + fuel[VehicleType.CAR] * MARKET_SHARES['other']
        )
        return count_vehicles * fuel_consumption * emission_factors['fuel'] / 1000000 * 365

    match road_type:
        case 'motorway':
            return count_vehicles * emission_factors['motorway'] / 1000000 * 365
        case 'inside':
            return count_vehicles * emission_factors['inside'] / 1000000 * 365
        case 'outside':
            return count_vehicles * emission_factors['outside'] / 1000000 * 365
        case _:
            return np.nan


def get_fuel_consumption(vehicle: VehicleType, speed: int) -> float:
    match vehicle:
        case VehicleType.CAR:
            return (54.7 + (496 / speed) + (-0.542) * speed + 0.0042 * speed**2) / DENSITY_PETROL
        case VehicleType.MOTORCYCLE:
            return (25.722 + (276.13 / speed) + (-0.254) * speed + 0.00311 * speed**2) / DENSITY_PETROL
        case VehicleType.RIGID_TRUCK:
            return (152.96 + (604.156 / speed) + (-2.295) * speed + 0.0238 * speed**2) / DENSITY_DIESEL
        case VehicleType.ARTICULATED_TRUCK:
            return (332.603 + (1680.879 / speed) + (-4.676) * speed + 0.0311 * speed**2) / DENSITY_DIESEL
        case VehicleType.BUS:
            return (281.735 + (4186.178 / speed) + (-3.457) * speed + 0.0216 * speed**2) / DENSITY_DIESEL


def get_emission_artifacts(emissions_gdf: gpd.GeoDataFrame, resources: ComputationResources) -> list[Artifact]:
    emission_artifacts = []
    for gas in EmissionsFactors:
        emission_artifacts.append(build_traffic_emissions_artifact(gas, emissions_gdf, resources))

    return emission_artifacts


def plot_emission_bar(df, gas, city, unit_name, unit_column) -> go.Figure:
    gas_name = gas.value.get('name')
    display_name = gas.value.get('display_name')
    column = f't_{gas_name}_{unit_column}'
    overall_mean = df[column].mean()
    overall_row = pd.Series({'name': city, column: overall_mean})
    overall_df = overall_row.to_frame().transpose()

    df_augmented = pd.concat([df.copy(), overall_df], ignore_index=True)
    df_sorted = df_augmented.sort_values(by=column)

    color_series = df_sorted.apply(
        lambda row: '#d62728' if (row['name'] == city and row[column] == overall_mean) else '#1f77b4', axis=1
    )
    colors = color_series.to_list()

    x_values = pd.to_numeric(df_sorted[column], errors='coerce').round(1)

    fig = go.Figure()

    fig.add_trace(
        go.Bar(
            x=x_values,
            y=df_sorted['name'],
            orientation='h',
            marker_color=colors,
            name=column,
        )
    )

    fig.update_layout(
        xaxis_title=f'Mean annual {display_name} emissions [{unit_name}]',
        yaxis_title='District',
        yaxis=dict(automargin=True),
        showlegend=False,
        template='plotly_white',
        height=200 + len(df_sorted) * 15,
    )

    return fig


def build_traffic_emissions_artifact(
    gas: EmissionsFactors, emissions_gdf: gpd.GeoDataFrame, resources: ComputationResources
) -> Artifact:
    gas_name = gas.value.get('name')
    display_name = gas.value.get('display_name')
    color, legend = get_colors_legend(emissions_gdf[f't_{gas_name}_km_yr'])
    emissions_gdf['color'] = color
    emissions_gdf[f't_{gas_name}_km_yr'] = emissions_gdf[f't_{gas_name}_km_yr'].round(2)
    description_path = f'resources/artifact_descriptions/traffic_emissions_description/{gas_name}.md'
    traffic_emissions_metadata = ArtifactMetadata(
        name=f'Annual {display_name} emissions [t/road-km]',
        tags={Topic.MAPS},
        filename=f'traffic_{gas_name}_emissions',
        summary=f'Estimated {display_name} emissions of road traffic [t per road-km per year]',
        description=Path(description_path).read_text(),
    )

    return create_vector_artifact(
        data=emissions_gdf,
        metadata=traffic_emissions_metadata,
        legend=Legend(legend_data=legend),
        label=f't_{gas_name}_km_yr',
        resources=resources,
    )


def get_emission_chart_artifacts(
    mean_df: pd.DataFrame,
    aoi_properties: AoiProperties,
    emission_sums: dict,
    resources: ComputationResources,
) -> list:
    city_name = aoi_properties.name
    if city_name in mean_df['name'].values:
        mean_df.loc[mean_df['name'] == city_name, 'name'] = f'{city_name} (core area)'
        city_name = f'{city_name} (whole area)'
    chart_artifacts = []
    for gas in EmissionsFactors:
        for unit in UNITS:
            gas_name = gas.value.get('name')
            display_name = gas.value.get('display_name')
            emission_sum = round(emission_sums[gas_name], 2)
            unit_name = UNITS[unit]['unit']
            unit_column = UNITS[unit]['column']
            description_template = Path(
                'resources/artifact_descriptions/traffic_emission_chart_description.md'
            ).read_text()
            description = description_template.format(
                gas=display_name, city=city_name, total_emissions=f'{emission_sum:n}', unit=unit_name
            )
            figure = plot_emission_bar(mean_df, gas, city_name, unit_name, unit_column)
            emission_chart_metadata = ArtifactMetadata(
                name=f'Mean annual {display_name} emissions [{unit_name}]',
                summary=f'Mean estimated annual {display_name} emissions of road traffic per city district [{unit_name}]',
                description=description,
                filename=f'traffic_{gas_name}_{unit_column}_emissions_chart',
                tags={Topic.CHARTS},
            )
            artifact = create_plotly_chart_artifact(
                figure=figure,
                metadata=emission_chart_metadata,
                resources=resources,
            )
            chart_artifacts.append(artifact)

    return chart_artifacts
