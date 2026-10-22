import json
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from render_card import card
import aggregate_activity as ag


def published():
    return json.loads((Path(__file__).resolve().parents[1] / 'data/activity-summary.json').read_text(encoding='utf-8'))


def test_card_uses_aggregate_and_separate_periods():
    data = published()
    svg = card(data)
    ET.fromstring(svg)
    assert str(sum(m['commits'] for m in data['meses'].values())) in svg
    assert str(sum(m['fechadas'] for m in data['issues'].values())) in svg
    assert '2026-07 a 2026-10' in svg
    assert 'Issues: 2026-08 a 2026-10' in svg
    assert data['snapshot_date'] in svg
    assert 'aria-labelledby="title desc"' in svg


def test_card_refuses_inconsistent_totals():
    data = published()
    data['total_commits'] += 1
    with pytest.raises(ValueError):
        card(data)


def test_missing_issues_differs_from_zero():
    data = published()
    data.pop('issues')
    assert '>—</text>' in card(data)
    data['issues'] = {}
    assert '>0</text>' in card(data)


def test_write_regenerates_card_and_preserves_snapshot(tmp_path):
    # An isolated synthetic repository; never an institutional source.
    import subprocess
    def git(*args):
        subprocess.run(['git', '-C', str(tmp_path), *args], check=True, capture_output=True)
    git('init', '-q')
    git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-m', 'feat: synthetic')
    out = tmp_path / 'output'
    args = ['--repo', str(tmp_path), '--author', 'test@example.invalid', '--out', str(out), '--write']
    ag.main(args)
    target = out / 'assets/engineering-activity-card.svg'
    original = target.read_text(encoding='utf-8')
    target.write_text('stale', encoding='utf-8')
    ag.main(args)
    assert target.read_text(encoding='utf-8') == original
    assert 'test@example.invalid' not in original
