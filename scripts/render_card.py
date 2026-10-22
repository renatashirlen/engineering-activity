"""Render the public card from the reviewed aggregate, never from private records."""
import argparse
import json
from datetime import date
from html import escape
from pathlib import Path


def card(summary):
    months = summary['meses']
    for field, total in [('commits', 'total_commits'), ('dias_ativos', 'total_dias_ativos'), ('versoes', 'total_versoes')]:
        if sum(m[field] for m in months.values()) != summary[total]:
            raise ValueError(f'Inconsistent aggregate: {total}')
    keys = sorted(months)
    period = f'{keys[0]} a {keys[-1]}' if keys else 'Sem atividade'
    snapshot = summary.get('snapshot_date')
    if snapshot:
        date.fromisoformat(snapshot)
    stamp = f'Snapshot: {snapshot}' if snapshot else 'Data do snapshot não registrada'
    issues = summary.get('issues')
    issue_keys = sorted(issues or {})
    issue_period = f'Issues: {issue_keys[0]} a {issue_keys[-1]}' if issue_keys else 'Issues: sem dados publicados'
    values = [summary['total_commits'], summary['total_dias_ativos'], sum(i['fechadas'] for i in issues.values()) if issues is not None else '—']
    labels = ['Commits', 'Dias ativos', 'Issues fechadas']
    description = f'{period}. {stamp}. ' + '; '.join(f'{v} {l}' for v, l in zip(values, labels)) + f'. {issue_period}. Último mês pode ser parcial. Contagens de atividade, não produtividade.'
    cells = ''.join(f'<text x="{26 + i * 206}" y="115" class="number">{v}</text><text x="{26 + i * 206}" y="143" class="label">{l}</text>' for i, (v, l) in enumerate(zip(values, labels)))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 660 260" role="img" aria-labelledby="title desc">
<title id="title">Engineering Activity — Renata Shirlen</title><desc id="desc">{escape(description)}</desc>
<style>text{{font-family:Segoe UI,Arial,sans-serif}}.number{{font-size:34px;font-weight:700;fill:#F9A8D4}}.label{{font-size:17px;fill:#F5E9FF}}.note{{font-size:14px;fill:#F5E9FF}}</style>
<rect x="1" y="1" width="658" height="258" rx="18" fill="#171224" stroke="#C084FC"/>
<path d="M26 26H72" stroke="#7C3AED" stroke-width="5"/>
<text x="26" y="58" fill="#C084FC" font-size="22" font-weight="700">Engineering Activity</text>
{cells}<text x="26" y="180" class="note">{escape(period)} · último mês pode ser parcial</text>
<text x="26" y="205" class="note">{escape(issue_period)}</text>
<text x="26" y="234" class="note">{escape(stamp)} · Agregados públicos; sem dados individuais</text></svg>
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    expected = card(json.loads((root / 'data/activity-summary.json').read_text(encoding='utf-8')))
    path = root / 'assets/engineering-activity-card.svg'
    if args.check:
        return 0 if path.exists() and path.read_text(encoding='utf-8') == expected else 1
    path.write_text(expected, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
