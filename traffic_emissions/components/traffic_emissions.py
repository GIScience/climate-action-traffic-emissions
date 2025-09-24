import logging
from enum import Enum
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import shapely
from climatoology.base.artifact import _Artifact, create_geojson_artifact, create_plotly_chart_artifact
from climatoology.base.baseoperator import AoiProperties
from climatoology.base.computation import ComputationResources
from ohsome import OhsomeClient

from traffic_emissions.components.utils import (
    DENSITY_DIESEL,
    DENSITY_PETROL,
    MARKET_SHARES,
    Topic,
    VehicleType,
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
        'cap': 3000,
    }
    CO = {  # dead: disable
        'name': 'CO',
        'column': 't_CO_km_yr',
        'fuel': 39.4,
        'motorway': 3.36,
        'inside': 3.25,
        'outside': 2.54,
        'cap': 50,
    }
    NOx = {  # dead: disable
        'name': 'NOx',
        'column': 't_NOx_km_yr',
        'fuel': 6.3,
        'motorway': 0.54,
        'inside': 0.52,
        'outside': 0.41,
        'cap': 8,
    }


def traffic_emissions(road_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    log.info('Calculating annual traffic emissions')
    traffic_gdf = preprocess(road_gdf)
    emissions_gdf = calculate_emissions(traffic_gdf)
    return emissions_gdf


def get_emission_sums(emissions_gdf: gpd.GeoDataFrame) -> dict:
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
    return emission_sums


def preprocess(gdf_traffic: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Preprocesses gdf_traffic for emission calculation.

    @param gdf_traffic: GeoDataFrame of OSM road network with estimated traffic volumes
    @return: gdf_traffic: GeoDataFrame with roads and their attributes (inside city / outside city / motorway)
    """
    built_up = gpd.read_file('resources/built_up.gpkg')
    gdf_traffic['road_type'] = 'outside'
    joined = gpd.sjoin(gdf_traffic, built_up, how='inner', predicate='intersects')
    gdf_traffic.loc[joined.index, 'road_type'] = 'inside'
    gdf_traffic.loc[
        gdf_traffic['highway'].isin(
            [
                'motorway',
                'motorway_1',
                'motorway_2',
                'motorway_3',
                'motorway_4',
                'motorway_link',
                'motorway_link_1',
                'motorway_link_2',
                'motorway_link_3',
            ]
        ),
        'road_type',
    ] = 'motorway'
    gdf_traffic.maxspeed = pd.to_numeric(gdf_traffic.maxspeed, errors='coerce').astype('Int64')
    return gdf_traffic


def calculate_emissions(gdf_traffic: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Calculates CO2, CO, and NOx emissions [g per day] of each road segment.

    @param gdf_traffic: GeoDataFrame with roads and their attributes (inside city / outside city / motorway)
    @return: traffic_gdf: GeoDataFrame with road segments and their CO2, CO, and NOx emissions [t per road-km per year]
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

    @param row: OSM road segment
    @param emission_factors: Emission factors for fuel consumption, motorways, inside city, and outside city [g per vehicle-km]
    @return: Emissions of the road segment [t per road-km per year]
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


def get_emission_artifacts(emissions_gdf: gpd.GeoDataFrame, resources: ComputationResources) -> list[_Artifact]:
    emission_artifacts = []
    for gas in EmissionsFactors:
        emission_artifacts.append(build_traffic_emissions_artifact(gas, emissions_gdf, resources))

    return emission_artifacts


def get_district_summaries(
    emissions_gdf: gpd.GeoDataFrame,
    aoi: shapely.MultiPolygon,
    ohsome_client: OhsomeClient,
) -> pd.DataFrame | None:
    log.info('Creating summary charts of emissions by city district')
    minimum_keys = ['admin_level', 'name']
    boundaries = ohsome_client.elements.geometry.post(
        properties='tags',
        bpolys=aoi,
        filter='geometry:polygon and boundary=administrative and admin_level=9',
        clipGeometry=True,
    ).as_dataframe(explode_tags=minimum_keys)
    boundaries = boundaries.loc[boundaries.geometry.geom_type.isin(('MultiPolygon', 'Polygon'))]
    boundaries = boundaries[boundaries.is_valid]
    boundaries = boundaries.reset_index(drop=True)
    if boundaries.shape[0] <= 1:
        return None
    else:
        log.debug(f'Summarising emissions into {boundaries.shape[0]} boundaries')
        boundaries = boundaries.to_crs(boundaries.estimate_utm_crs())
        emissions_gdf = emissions_gdf[emissions_gdf.geometry.type.isin(['LineString', 'MultiLineString'])]
        emissions_gdf = emissions_gdf.overlay(boundaries, how='identity', keep_geom_type=False)
        mean_df = emissions_gdf.groupby('name')[['t_CO2_km_yr', 't_CO_km_yr', 't_NOx_km_yr']].mean().reset_index()
        return mean_df


def plot_emission_bar(df, gas, city) -> go.Figure:
    column = f't_{gas}_km_yr'
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
        xaxis_title=f'Mean annual {gas} emissions [t/road-km]',
        yaxis_title='District',
        yaxis=dict(automargin=True),
        showlegend=False,
        template='plotly_white',
        height=200 + len(df_sorted) * 15,
    )

    return fig


def build_traffic_emissions_artifact(
    gas: EmissionsFactors, emissions_gdf: gpd.GeoDataFrame, resources: ComputationResources
) -> _Artifact:
    gas_name = gas.value.get('name')
    color, legend = get_colors_legend(gas.value['cap'], emissions_gdf[f't_{gas_name}_km_yr'])

    return create_geojson_artifact(
        features=emissions_gdf.geometry,
        layer_name=f'Annual {gas_name} emissions [t/road-km]',
        caption=f'Estimated {gas_name} emissions of road traffic [t per road-km per year]',
        description=Path('resources/artifact_descriptions/traffic_emissions_description.md').read_text(),
        color=color,
        legend_data=legend,
        label=emissions_gdf[f't_{gas_name}_km_yr'].round(2),
        resources=resources,
        filename=f'traffic_{gas_name}_emissions',
        tags={Topic.MAPS},
    )


def get_emission_chart_artifacts(
    mean_df: pd.DataFrame,
    aoi_properties: AoiProperties,
    emission_sums: dict,
    resources: ComputationResources,
) -> list:
    city_name = aoi_properties.name
    chart_artifacts = []
    for gas in EmissionsFactors:
        gas_name = gas.value.get('name')
        emission_sum = str(round(emission_sums[gas_name], 2))
        description_template = Path('resources/artifact_descriptions/traffic_emission_chart_description.md').read_text()
        description = description_template.format(gas=gas_name, city=city_name, total_emissions=emission_sum)
        figure = plot_emission_bar(mean_df, gas_name, city_name)
        artifact = create_plotly_chart_artifact(
            figure=figure,
            title=f'Mean annual {gas_name} emissions [t/road-km]',
            caption=f'Mean estimated {gas_name} emissions of road traffic per city district [t per road-km per year]',
            description=description,
            resources=resources,
            filename=f'traffic_{gas_name}_emissions_chart',
            tags={Topic.CHARTS},
        )
        chart_artifacts.append(artifact)

    return chart_artifacts
