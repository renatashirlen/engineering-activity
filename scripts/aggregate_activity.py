#!/usr/bin/env python3
"""Agrega commits por mês a partir de um repositório Git local (somente leitura).

Saída contém apenas contagens mensais: sem mensagens, e-mails, hashes ou arquivos.
Padrão é --dry-run; use --write para gravar (e só grava se os números mudaram).

Uso:
  aggregate_activity.py --repo ~/desenvolvimento/rsc-tae --author a@x.br [--author b@x.br] [--write]
"""
import argparse
import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, datetime
from statistics import median
from pathlib import Path

BUMP = re.compile(r"^chore(\([^)]*\))?!?:\s*(bump\b|ajusta vers[aã]o|prepara vers[aã]o)", re.I)
SEP_R, SEP_C = "\x1e", "\x1f"


def git_log(repo, authors):
    cmd = ["git", "-C", str(repo), "log", "--all", "--no-merges",
           f"--format={SEP_R}%H{SEP_C}%ae{SEP_C}%ad{SEP_C}%s",
           "--date=format:%Y-%m"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    wanted = {a.lower() for a in authors}
    seen = set()
    for rec in out.split(SEP_R):
        if not rec.strip():
            continue
        h, email, month, subject = (rec.split(SEP_C) + [""] * 4)[:4]
        if h in seen or email.lower() not in wanted:
            continue
        seen.add(h)
        yield month, subject


def aggregate(commits):
    months = defaultdict(lambda: {"commits": 0, "bumps_excluidos": 0})
    for month, subject in commits:
        m = months[month]
        if BUMP.search(subject):
            m["bumps_excluidos"] += 1
            continue
        m["commits"] += 1
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
    ".bg{fill:#fff}.t{fill:#111}.g{stroke:#d0d7de}.b{fill:#2563eb}.c{fill:#0f766e}"
    "@media (prefers-color-scheme:dark){.bg{fill:#0d1117}.t{fill:#e6edf3}.g{stroke:#30363d}"
    ".b{fill:#58a6ff}.c{fill:#3fb9a8}}"
    "</style>"
)


def svg(months):
    w, h, pad, bw = 60 + 56 * len(months), 236, 30, 36
    now = current_month()
    top = max((m["commits"] for m in months.values()), default=1) or 1
    area = h - 2 * pad - 20
    base = h - pad
    grid = []
    for frac in (0.5, 1.0):
        gy = base - int(area * frac)
        grid.append(f'<line class="g" x1="40" x2="{w - 10}" y1="{gy}" y2="{gy}" stroke-dasharray="3 3"/>'
                    f'<text class="t" x="34" y="{gy + 4}" text-anchor="end" font-size="10">{round(top * frac)}</text>')
    bars = []
    for i, (k, m) in enumerate(months.items()):
        bh = int(area * m["commits"] / top)
        x, y = 50 + i * 56, base - bh
        cls = "c" if k == now else "b"
        bars.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{bw}" height="{bh}" rx="3"/>'
                    f'<text class="t" x="{x + bw / 2}" y="{y - 4}" text-anchor="middle" font-size="11">{m["commits"]}</text>'
                    f'<text class="t" x="{x + bw / 2}" y="{h - 14}" text-anchor="middle" font-size="11">{label(k, k == now)}</text>')
    note = (f'<text class="t" x="40" y="{h - 2}" font-size="10">* mês parcial</text>'
            if now in months else "")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="Commits por mês, sem merges e sem bumps de versão" font-family="sans-serif">'
            f'<title>Commits por mês (sem merges e sem bumps)</title>{STYLE}'
            f'<rect class="bg" width="{w}" height="{h}" rx="8"/>{"".join(grid)}{"".join(bars)}{note}</svg>\n')


def write_if_changed(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() == text:
        return False
    path.write_text(text)
    return True


def readme_table(summary):
    issues = summary.get("issues", {})
    rows = ["| Mês | Commits | Issues fechadas | Mediana até fechar (dias) |", "|---|---:|---:|---:|"]
    for k, m in summary["meses"].items():
        i = issues.get(k)
        rows.append(f"| {label(k, k == current_month())} | {m['commits']} | "
                    f"{i['fechadas'] if i else '–'} | {i['mediana_dias'] if i else '–'} |")
    ti = sum(i["fechadas"] for i in issues.values())
    rows.append(f"| **Total** | **{summary['total_commits']}** | **{ti if issues else '–'}** | |")
    return "\n".join(rows)


def update_readme(path, summary):
    start, end = "<!-- stats:start -->", "<!-- stats:end -->"
    if not path.exists():
        return False
    text = path.read_text()
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
        "primeiro_mes": next(iter(months), None),
        "criterios": "sem merges, sem bumps de versão, hashes únicos entre ramos",
    }
    if a.issues_json:
        summary["issues"] = aggregate_issues(json.loads(Path(a.issues_json).read_text()))
        summary["criterio_issues"] = "issues abertas por mim e já fechadas; mês do fechamento"
    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if a.check:
        atual = Path(a.out) / "data" / "activity-summary.json"
        mudou = not atual.exists() or atual.read_text() != text
        print("mudou" if mudou else "sem mudanças")
        return 10 if mudou else 0
    if not a.write:
        print(text)
        print("(dry-run: nada gravado)", file=sys.stderr)
        return 0
    out = Path(a.out)
    c1 = write_if_changed(out / "data" / "activity-summary.json", text)
    c2 = write_if_changed(out / "assets" / "activity-chart.svg", svg(months))
    c3 = update_readme(out / "README.md", summary)
    print("atualizado" if c1 or c2 or c3 else "sem mudanças")
    return 0


if __name__ == "__main__":
    sys.exit(main())
