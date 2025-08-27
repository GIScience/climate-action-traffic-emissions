import pandas as pd
from climatoology.base.artifact import ContinuousLegendData
from pydantic_extra_types.color import Color

from traffic_emissions.components.utils import get_colors_legend


def test_get_colors_legend():
    expected_colors = pd.Series([Color('#feb24c'), Color('#e2191c'), Color('#800026')])
    expected_legend = ContinuousLegendData(cmap_name='YlOrRd', ticks={'> 4': 1.0, '0': 0.0})
    colors, legend = get_colors_legend(4, pd.Series([1.5, 3.0, 4.5]))

    assert colors.to_list() == expected_colors.to_list()
    assert legend == expected_legend
