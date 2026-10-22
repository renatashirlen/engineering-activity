#!/usr/bin/env python3
"""Agrega commits por mês a partir de um repositório Git local (somente leitura).

Saída contém apenas contagens mensais: sem mensagens, e-mails, hashes ou arquivos.
Padrão é --dry-run; use --write para gravar (e só grava se os números mudaram).

Uso:
  aggregate_activity.py --repo ~/desenvolvimento/rsc-tae --author a@x.br [--author b@x.br] [--write]
"""
import argparse
import math
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime
from statistics import median
from pathlib import Path
from render_card import card

BUMP = re.compile(r"^chore(\([^)]*\))?!?:\s*(bump\b|ajusta vers[aã]o|prepara vers[aã]o)", re.I)
SEP_R, SEP_C = "\x1e", "\x1f"


def git_log(repo, authors):
    cmd = ["git", "-C", str(repo), "log", "--all", "--no-merges",
           f"--format={SEP_R}%H{SEP_C}%ae{SEP_C}%ad{SEP_C}%s",
           "--date=format:%Y-%m-%d"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    wanted = {a.lower() for a in authors}
    seen = set()
    for rec in out.split(SEP_R):
        if not rec.strip():
            continue
        h, email, dia, subject = (rec.split(SEP_C) + [""] * 4)[:4]
        if h in seen or email.lower() not in wanted:
            continue
        seen.add(h)
        yield dia[:7], subject, dia


VERSAO = re.compile(r"\d+\.\d+\.\d+")


def aggregate(commits):
    months = defaultdict(lambda: {"commits": 0, "bumps_excluidos": 0})
    primeira = {}  # versão -> primeiro mês em que apareceu (conta uma vez só)
    dias = defaultdict(set)  # dias distintos com algum commit (inclui bumps), por mês
    for item in commits:
        month, subject = item[0], item[1]
        m = months[month]
        if len(item) > 2:
            dias[month].add(item[2])
        if BUMP.search(subject):
            m["bumps_excluidos"] += 1
            v = VERSAO.findall(subject)
            if v:
                primeira[v[-1]] = min(month, primeira.get(v[-1], month))
            continue
        m["commits"] += 1
    for mes in primeira.values():
        months[mes]["versoes"] = months[mes].get("versoes", 0) + 1
    for k, m in months.items():
        m.setdefault("versoes", 0)
        m["dias_ativos"] = len(dias[k])
    return {k: months[k] for k in sorted(months)}


def aggregate_issues(rows):
    """rows: [{"created_at": ISO, "closed_at": ISO}] -> contagem e mediana de dias por mês de fechamento."""
    por_mes = defaultdict(list)
    for r in rows:
        if not r.get("closed_at"):
            continue
        ini = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
        fim = datetime.fromisoformat(r["closed_at"].replace("Z", "+00:00"))
        por_mes[fim.strftime("%Y-%m")].append(max((fim - ini).total_seconds() / 86400, 0))
    return {k: {"fechadas": len(v), "mediana_dias": round(median(v), 1)} for k, v in sorted(por_mes.items())}


MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def label(key, partial=False):
    ano, mes = key.split("-")
    return f"{MESES[int(mes) - 1]}/{ano[2:]}" + ("*" if partial else "")


def current_month():
    return date.today().strftime("%Y-%m")


STYLE = (
    "<style>"
    ".bg{fill:#F5E9FF}.t{fill:#171224}.g{stroke:#887496}.b{fill:#7C3AED}.c{fill:#7C3AED}"
    "@media (prefers-color-scheme:dark){.bg{fill:#171224}.t{fill:#F5E9FF}.g{stroke:#887496}"
    ".b{fill:#C084FC}.c{fill:#F9A8D4}}"
    "</style>"
)


def axis_scale(maximum):
    """About five intervals with round integer ticks and room for the largest bar."""
    raw = max(maximum, 1) / 5
    power = 10 ** math.floor(math.log10(raw))
    step = max(1, next(n * power for n in (1, 2, 5, 10) if n * power >= raw))
    return math.ceil(max(maximum, 1) / step) * step, step


def svg(months, snapshot_date=None):
    w, h, left, right, top, base = max(560, 100 + 76 * len(months)), 340, 72, 24, 60, 260
    now = snapshot_date[:7] if snapshot_date else current_month()
    ceiling, step = axis_scale(max((m["commits"] for m in months.values()), default=0))
    area = base - top
    grid = []
    for tick in range(0, int(ceiling) + 1, int(step)):
        gy = base - area * tick / ceiling
        grid.append(f'<line class="g" x1="{left}" x2="{w - right}" y1="{gy}" y2="{gy}" stroke-dasharray="3 3"/>'
                    f'<text class="t" x="{left - 10}" y="{gy + 4}" text-anchor="end" font-size="13">{tick}</text>')
    bars = []
    slot = (w - left - right) / max(len(months), 1)
    bw = min(48, slot * .6)
    for i, (k, m) in enumerate(sorted(months.items())):
        bh = area * m["commits"] / ceiling
        x, y = left + (i + .5) * slot - bw / 2, base - bh
        cls = "c" if k == now else "b"
        bars.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{bw}" height="{bh}" rx="3"/>'
                    f'<text class="t" x="{x + bw / 2}" y="{y - 8}" text-anchor="middle" font-size="14">{m["commits"]}</text>'
                    f'<text class="t" x="{x + bw / 2}" y="{base + 23}" text-anchor="middle" font-size="13">{label(k, k == now)}</text>')
    note = (f'<text class="t" x="{left}" y="330" font-size="12">* mês parcial no snapshot</text>' if now in months else "")
    description = "; ".join(f"{label(k, k == now)}: {m['commits']} commits" for k, m in sorted(months.items())) or "Sem atividade"
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" '
            f'aria-labelledby="title desc" font-family="sans-serif">'
            f'<title id="title">Commits por mês (sem merges e sem bumps)</title>'
            f'<desc id="desc">Eixo horizontal: mês/ano. Eixo vertical: quantidade de commits. {description}.</desc>{STYLE}'
            f'<rect class="bg" width="{w}" height="{h}" rx="8"/>'
            f'<text class="t" x="{left}" y="28" font-size="18" font-weight="700">Commits por mês</text>'
            f'{"".join(grid)}<path class="g" d="M{left} {top}V{base}H{w-right}" fill="none"/>'
            f'{"".join(bars)}'
            f'<text class="t" x="20" y="160" transform="rotate(-90 20 160)" text-anchor="middle" font-size="14">Quantidade de commits</text>'
            f'<text class="t" x="{(left+w-right)/2}" y="309" text-anchor="middle" font-size="14">Mês/ano</text>'
            f'{note}</svg>\n')


def write_if_changed(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.write_text(text, encoding="utf-8")
    return True


def readme_table(summary):
    issues = summary.get("issues", {})
    rows = ["| Mês | Commits | Dias ativos | Versões | Issues fechadas | Mediana até fechar (dias) |", "|---|---:|---:|---:|---:|---:|"]
    for k, m in summary["meses"].items():
        i = issues.get(k)
        rows.append(f"| {label(k, k == current_month())} | {m['commits']} | {m['dias_ativos']} | {m['versoes']} | "
                    f"{i['fechadas'] if i else '–'} | {i['mediana_dias'] if i else '–'} |")
    ti = sum(i["fechadas"] for i in issues.values())
    rows.append(f"| **Total** | **{summary['total_commits']}** | **{summary['total_dias_ativos']}** | **{summary['total_versoes']}** | **{ti if issues else '–'}** | |")
    return "\n".join(rows)


def update_readme(path, summary):
    start, end = "<!-- stats:start -->", "<!-- stats:end -->"
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    if start not in text or end not in text:
        return False
    head, rest = text.split(start, 1)
    tail = rest.split(end, 1)[1]
    return write_if_changed(path, f"{head}{start}\n{readme_table(summary)}\n{end}{tail}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--author", action="append", required=True, help="e-mail verificado (repetível)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent))
    ap.add_argument("--issues-json", help="exportação privada [{created_at, closed_at}] (fora do repositório)")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="não grava; sai com código 10 se os números diferem dos publicados")
    a = ap.parse_args(argv)

    months = aggregate(git_log(a.repo, a.author))
    summary = {
        "meses": months,
        "total_commits": sum(m["commits"] for m in months.values()),
        "total_dias_ativos": sum(m["dias_ativos"] for m in months.values()),
        "total_versoes": sum(m["versoes"] for m in months.values()),
        "primeiro_mes": next(iter(months), None),
        "criterios": "sem merges, sem bumps de versão, hashes únicos entre ramos",
    }
    if a.issues_json:
        summary["issues"] = aggregate_issues(json.loads(Path(a.issues_json).read_text(encoding="utf-8")))
        summary["criterio_issues"] = "issues abertas por mim e já fechadas; mês do fechamento"
    # Preserve the reviewed snapshot date while counts are unchanged.
    published = Path(a.out) / "data" / "activity-summary.json"
    previous = json.loads(published.read_text(encoding="utf-8")) if published.exists() else {}
    previous_date = previous.pop("snapshot_date", None)
    summary["snapshot_date"] = previous_date if previous == summary and previous_date else date.today().isoformat()
    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if a.check:
        atual = Path(a.out) / "data" / "activity-summary.json"
        mudou = not atual.exists() or atual.read_text(encoding="utf-8") != text
        print("mudou" if mudou else "sem mudanças")
        return 10 if mudou else 0
    if not a.write:
        print(text)
        print("(dry-run: nada gravado)", file=sys.stderr)
        return 0
    out = Path(a.out)
    c1 = write_if_changed(out / "data" / "activity-summary.json", text)
    c2 = write_if_changed(out / "assets" / "activity-chart.svg", svg(months, summary["snapshot_date"]))
    c3 = update_readme(out / "README.md", summary)
    c4 = write_if_changed(out / "assets" / "engineering-activity-card.svg", card(summary))
    print("atualizado" if c1 or c2 or c3 or c4 else "sem mudanças")
    return 0


if __name__ == "__main__":
    sys.exit(main())
