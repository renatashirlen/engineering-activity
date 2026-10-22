import subprocess, sys, tempfile, json, os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import aggregate_activity as ag


def sh(repo, *args, env=None):
    subprocess.run(["git", "-C", repo, *args], check=True, capture_output=True,
                   env={**os.environ, **(env or {})})


def make_repo():
    d = tempfile.mkdtemp()
    sh(d, "init", "-q", "-b", "main")
    def commit(msg, email, date):
        env = {"GIT_AUTHOR_NAME": "T", "GIT_AUTHOR_EMAIL": email, "GIT_COMMITTER_NAME": "T",
               "GIT_COMMITTER_EMAIL": email, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
        sh(d, "commit", "-q", "--allow-empty", "-m", msg, env=env)
    return d, commit


def test_exclui_merge_bump_e_outros_autores():
    d, c = make_repo()
    c("feat: a", "eu@x.br", "2026-08-01T10:00:00")
    c("feat: b\n\nCo-Authored-By: Claude <n@a.com>", "eu@x.br", "2026-08-02T10:00:00")
    c("chore(release): bump de versao para 0.1.1", "eu@x.br", "2026-08-03T10:00:00")
    c("feat: de outra pessoa", "outro@x.br", "2026-08-04T10:00:00")
    sh(d, "checkout", "-q", "-b", "f")
    c("feat: no ramo", "eu@x.br", "2026-09-01T10:00:00")
    sh(d, "checkout", "-q", "main")
    sh(d, "merge", "-q", "--no-ff", "f", "-m", "Merge f")
    r = ag.aggregate(ag.git_log(d, ["EU@x.br"]))
    assert r["2026-08"] == {"commits": 2, "bumps_excluidos": 1, "versoes": 1}
    assert r["2026-09"]["commits"] == 1


def test_idempotente_e_dry_run():
    d, c = make_repo()
    c("feat: a", "eu@x.br", "2026-08-01T10:00:00")
    out = tempfile.mkdtemp()
    base = ["--repo", d, "--author", "eu@x.br", "--out", out]
    ag.main(base)
    assert not (Path(out) / "data").exists()
    assert ag.main(base + ["--write"]) == 0
    first = (Path(out) / "data/activity-summary.json").read_text()
    assert "eu@x.br" not in first and "feat" not in first
    assert not ag.write_if_changed(Path(out) / "data/activity-summary.json", first)


def test_regex_de_bump_so_pega_commits_de_versao():
    bumps = ["chore(release): bump de versao para 0.1.100 (#1)", "chore: bump 0.1.198 e CHANGELOG",
             "chore(docker): bump versão da imagem", "chore(release): prepara versão 0.1.170 (#2)",
             "chore(frontend): ajusta versão para 0.1.90"]
    reais = ["fix: interceptor e bump de dependências com CVEs", "feat: tela nova",
             "chore: consolida MRs com bump único e renumera migration"]
    assert all(ag.BUMP.search(s) for s in bumps)
    assert not any(ag.BUMP.search(s) for s in reais)


def test_rotulo_de_mes_e_parcial():
    assert ag.label("2026-07") == "jul/26"
    assert ag.label("2026-10", True) == "out/26*"


def test_svg_com_tema_claro_e_escuro_e_mes_parcial():
    meses = {"2026-07": {"commits": 10, "bumps_excluidos": 0, "versoes": 0}}
    out = ag.svg(meses)
    assert "prefers-color-scheme:dark" in out and 'class="bg"' in out
    assert "* mês parcial" not in out or ag.current_month() in meses


def test_check_sinaliza_mudanca_sem_gravar():
    d, c = make_repo()
    c("feat: a", "eu@x.br", "2026-08-01T10:00:00")
    out = tempfile.mkdtemp()
    base = ["--repo", d, "--author", "eu@x.br", "--out", out]
    assert ag.main(base + ["--check"]) == 10
    assert not (Path(out) / "data").exists()
    ag.main(base + ["--write"])
    assert ag.main(base + ["--check"]) == 0
    c("feat: b", "eu@x.br", "2026-08-02T10:00:00")
    assert ag.main(base + ["--check"]) == 10


def test_periodo_sem_commits_do_autor():
    d, c = make_repo()
    c("feat: de outra pessoa", "outro@x.br", "2026-08-01T10:00:00")
    assert ag.aggregate(ag.git_log(d, ["eu@x.br"])) == {}


def test_issues_por_mes_com_mediana():
    rows = [{"created_at": "2026-09-01T00:00:00Z", "closed_at": "2026-09-03T00:00:00Z"},
            {"created_at": "2026-09-10T00:00:00Z", "closed_at": "2026-09-16T00:00:00Z"},
            {"created_at": "2026-09-10T00:00:00Z", "closed_at": None}]
    assert ag.aggregate_issues(rows) == {"2026-09": {"fechadas": 2, "mediana_dias": 4.0}}


def test_saida_sem_dados_de_issues_individuais():
    import json
    d, c = make_repo()
    c("feat: a", "eu@x.br", "2026-08-01T10:00:00")
    out = tempfile.mkdtemp()
    f = Path(out) / "x.json"
    f.write_text(json.dumps([{"created_at": "2026-08-01T00:00:00Z", "closed_at": "2026-08-02T00:00:00Z"}]))
    ag.main(["--repo", d, "--author", "eu@x.br", "--out", out, "--issues-json", str(f), "--write"])
    texto = (Path(out) / "data/activity-summary.json").read_text()
    assert "created_at" not in texto and "closed_at" not in texto and '"fechadas": 1' in texto


def test_versoes_contam_uma_vez_mesmo_com_varios_bumps():
    commits = [("2026-08", "chore(release): bump de versao para 0.1.5 (#1)"),
               ("2026-09", "chore(release): bump de versao para 0.1.5 (#2)"),
               ("2026-09", "chore(docker): bump versão da imagem 0.1.5 → 0.1.6"),
               ("2026-09", "feat: algo")]
    r = ag.aggregate(commits)
    assert r["2026-08"]["versoes"] == 1 and r["2026-09"]["versoes"] == 1
    assert r["2026-09"]["commits"] == 1 and r["2026-09"]["bumps_excluidos"] == 2
