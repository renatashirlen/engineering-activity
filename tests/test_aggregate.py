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
    assert r["2026-08"] == {"commits": 2, "com_ia": 1, "bumps_excluidos": 1}
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
