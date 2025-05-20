import importlib
import importlib.metadata
from pathlib import Path

from climatoology.base.info import PluginAuthor, _Info, generate_plugin_info
from semver import Version

from plugin_blueprint.core.input import ComputeInput


def get_info() -> _Info:
    authors = [PluginAuthor(name='Blueprint Author')]
    info = generate_plugin_info(
        name='Plugin Blueprint',
        icon=Path('resources/icon.jpeg'),
        authors=authors,
        version=Version.parse(importlib.metadata.version('plugin-blueprint')),
        concerns=set(),
        purpose=Path('resources/purpose.md'),
        teaser='A bare minimum example to act as a blueprint for new assessment tools on the CA Platform.',
        methodology=Path('resources/methodology.md'),
        demo_input_parameters=ComputeInput(),
    )
    return info
