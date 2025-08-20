import importlib
import importlib.metadata
import logging
from datetime import timedelta
from pathlib import Path

from climatoology.base.info import Concern, PluginAuthor, _Info, generate_plugin_info
from pydantic import HttpUrl
from semver import Version

from traffic_emissions.core.input import ComputeInput

log = logging.getLogger(__name__)


def get_info() -> _Info:
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
    info = generate_plugin_info(
        name='Traffic Emissions',
        icon=Path('resources/icon.jpeg'),
        authors=authors,
        version=Version.parse(importlib.metadata.version('traffic-emissions')),
        concerns={Concern.CLIMATE_ACTION__GHG_EMISSION},
        purpose=Path('resources/purpose.md'),
        teaser='Estimate annual carbon dioxide emissions from road traffic for any area within Germany.',
        methodology=Path('resources/methodology.md'),
        demo_input_parameters=ComputeInput(),
        computation_shelf_life=timedelta(weeks=24),
    )
    log.info(f'Return info {info.model_dump()}')

    return info
