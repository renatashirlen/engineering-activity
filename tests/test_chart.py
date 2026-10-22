import sys
from pathlib import Path
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import aggregate_activity as ag


def test_round_scale_covers_data_and_zero():
    assert ag.axis_scale(241) == (250, 50)
    for maximum in (0, 1, 3, 50, 250, 251, 1000):
        ceiling, step = ag.axis_scale(maximum)
        assert ceiling >= maximum and step >= 1
        assert ceiling % step == 0


def test_axes_and_exact_values_have_distinct_labels():
    svg = ag.svg({'2026-10': {'commits': 241}}, '2026-10-22')
    ET.fromstring(svg)
    assert '>250</text>' in svg and '>50</text>' in svg
    assert '>241</text>' in svg
    assert 'Quantidade de commits' in svg and 'Mês/ano' in svg
    assert 'out/26*' in svg and '* mês parcial no snapshot' in svg
    assert 'Eixo horizontal' in svg


def test_empty_chart_is_valid():
    ET.fromstring(ag.svg({}))
