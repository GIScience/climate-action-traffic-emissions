from datetime import timedelta
from pathlib import Path

import geopandas as gpd
from climatoology.base.aoi import CoveredByGeomConstraint
from climatoology.base.plugin_info import (
    Concern,
    PluginAuthor,
    PluginInfo,
    generate_plugin_info,
    get_climatoology_logger,
)
from pydantic import HttpUrl
from shapely.geometry import mapping

from traffic_emissions.core.input import ComputeInput

log = get_climatoology_logger(__name__)


def get_info() -> PluginInfo:
    authors = [
        PluginAuthor(
            name='Veit Ulrich',
            affiliation='HeiGIT gGmbH',
            website=HttpUrl('https://heigit.org/heigit-team/'),
        ),
        PluginAuthor(
            name='Sebastian Block',
            affiliation='HeiGIT gGmbH',
            website=HttpUrl('https://heigit.org/heigit-team/'),
        ),
        PluginAuthor(
            name='Emily Wilke',
            affiliation='HeiGIT gGmbH',
            website=HttpUrl('https://heigit.org/heigit-team/'),
        ),
    ]
    germany = gpd.read_file('resources/germany_buffered_boundaries.geojson').buffer(2500).to_crs(4326)
    aoi_constraints = [
        [
            CoveredByGeomConstraint(
                description='Germany',
                geom=mapping(germany.union_all()),
            ),
        ]
    ]

    info = generate_plugin_info(
        name='Traffic Emissions',
        icon=Path('resources/icon.jpeg'),
        authors=authors,
        concerns={Concern.CLIMATE_ACTION__GHG_EMISSION},
        purpose=Path('resources/purpose.md'),
        teaser='Estimate annual carbon dioxide emissions from road traffic for any area within Germany.',
        methodology=Path('resources/methodology.md'),
        demo_input_parameters=ComputeInput(),
        computation_shelf_life=timedelta(weeks=24),
        sources_library=Path('resources/sources.bib'),
        aoi_constraints=aoi_constraints,
    )
    log.info(f'Return info {info.model_dump()}')

    return info
