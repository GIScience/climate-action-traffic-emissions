import pandas as pd
from climatoology.base.artifact import ContinuousLegendData
from pydantic_extra_types.color import Color

from traffic_emissions.components.utils import get_colors_legend


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
