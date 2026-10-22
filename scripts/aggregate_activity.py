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
from pathlib import Path

BUMP = re.compile(r"^chore\((release|docker)\)|\bbump\b|ajusta vers[aã]o", re.I)
AI = re.compile(r"^co-authored-by:.*(claude|codex|gemini|anthropic|openai)", re.I | re.M)
SEP_R, SEP_C = "\x1e", "\x1f"


def git_log(repo, authors):
    cmd = ["git", "-C", str(repo), "log", "--all", "--no-merges",
           f"--format={SEP_R}%H{SEP_C}%ae{SEP_C}%ad{SEP_C}%s{SEP_C}%b",
           "--date=format:%Y-%m"]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True).stdout
    wanted = {a.lower() for a in authors}
    seen = set()
    for rec in out.split(SEP_R):
        if not rec.strip():
            continue
        h, email, month, subject, body = (rec.split(SEP_C) + [""] * 5)[:5]
        if h in seen or email.lower() not in wanted:
            continue
        seen.add(h)
        yield month, subject, body


def aggregate(commits):
    months = defaultdict(lambda: {"commits": 0, "com_ia": 0, "bumps_excluidos": 0})
    for month, subject, body in commits:
        m = months[month]
        if BUMP.search(subject):
            m["bumps_excluidos"] += 1
            continue
        m["commits"] += 1
        if AI.search(body):
            m["com_ia"] += 1
    return {k: months[k] for k in sorted(months)}


def svg(months):
    w, h, pad, bw = 40 + 56 * len(months), 220, 30, 36
    top = max((m["commits"] for m in months.values()), default=1) or 1
    bars = []
    for i, (k, m) in enumerate(months.items()):
        bh = int((h - 2 * pad - 20) * m["commits"] / top)
        x, y = 30 + i * 56, h - pad - bh
        bars.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" fill="#2563eb"/>'
                    f'<text x="{x + bw / 2}" y="{y - 4}" text-anchor="middle" font-size="11">{m["commits"]}</text>'
                    f'<text x="{x + bw / 2}" y="{h - 10}" text-anchor="middle" font-size="11">{k}</text>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" '
            f'aria-label="Commits por mês, sem merges e sem bumps de versão" '
            f'font-family="sans-serif" fill="#111">'
            f'<title>Commits por mês (sem merges e sem bumps)</title>{"".join(bars)}</svg>\n')


def write_if_changed(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() == text:
        return False
    path.write_text(text)
    return True


def readme_table(summary):
    rows = ["| Mês | Commits | Com assistência de IA registrada |", "|---|---:|---:|"]
    for k, m in summary["meses"].items():
        rows.append(f"| {k} | {m['commits']} | {m['com_ia']} |")
    rows.append(f"| **Total** | **{summary['total_commits']}** | **{summary['total_com_ia']}** |")
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
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args(argv)

    months = aggregate(git_log(a.repo, a.author))
    summary = {
        "meses": months,
        "total_commits": sum(m["commits"] for m in months.values()),
        "total_com_ia": sum(m["com_ia"] for m in months.values()),
        "primeiro_mes": next(iter(months), None),
        "criterios": "sem merges, sem bumps de versão, hashes únicos entre ramos",
    }
    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
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
