"""forkflow fetch / borrow / pr (README.md, "Forks, coworker remotes, PRs"). Throwaway repos: an upstream, a fork
(origin), a coworker remote, and a clone with all three."""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
KIT_GIT = ROOT / "src" / "forkflow" / "git"

pytestmark = pytest.mark.skipif(shutil.which("bash") is None or shutil.which("git") is None, reason="needs bash and git")


@pytest.fixture
def repos(tmp_path, monkeypatch):
    gc = tmp_path / "gitconfig"
    gc.write_text("[user]\n\tname = t\n\temail = t@t\n[init]\n\tdefaultBranch = main\n")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(gc))
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for var in ("GIT_PRIMARY_BRANCH", "GIT_PRIMARY_REMOTE", "GIT_PUSH_HOOK_SKIP"):
        monkeypatch.delenv(var, raising=False)
    git(tmp_path, "init", "-q", "--bare", "up.git")
    git(tmp_path, "init", "-q", "--bare", "fork.git")
    git(tmp_path, "init", "-q", "--bare", "mohit.git")
    git(tmp_path, "clone", "-q", "up.git", "seed")
    commit(tmp_path / "seed", "A")
    git(tmp_path / "seed", "push", "-q", "origin", "main")
    git(tmp_path, "clone", "-q", "fork.git", "me")
    me = tmp_path / "me"
    git(me, "remote", "add", "upstream", "../up.git")
    git(me, "fetch", "-q", "upstream")
    git(me, "checkout", "-q", "-B", "main", "upstream/main")
    git(me, "push", "-q", "origin", "main")
    git(tmp_path, "clone", "-q", "up.git", "mohit-wt")
    mw = tmp_path / "mohit-wt"
    git(mw, "checkout", "-q", "-b", "feat")
    commit(mw, "a.py", "from mohit\n")
    commit(mw, "b.py", "other\n")
    git(mw, "remote", "add", "fork", "../mohit.git")
    git(mw, "push", "-q", "fork", "feat")
    git(me, "remote", "add", "mohit", "../mohit.git")
    return tmp_path


def git(cwd, *args, check=True):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check)


def commit(cwd, name, content=None):
    (Path(cwd) / name).write_text(content if content is not None else name)
    git(cwd, "add", name)
    git(cwd, "commit", "-qm", name)


def run_script(script, cwd, *args, env=None):
    return subprocess.run(["bash", str(KIT_GIT / script), *args], cwd=cwd, capture_output=True, text=True,
                          env=env or os.environ.copy())


def fake_gh(tmp_path):
    """A gh that records its arguments, plus git and bash, and nothing else on PATH."""
    bindir = tmp_path / "bin"
    bindir.mkdir(parents=True)
    args = tmp_path / "gh-args"
    gh = bindir / "gh"
    gh.write_text('#!/bin/sh\nprintf \'%s\\n\' "$@" > "$GH_ARGS"\n')
    gh.chmod(0o755)
    os.symlink(shutil.which("git"), bindir / "git")
    os.symlink(shutil.which("bash"), bindir / "bash")
    env = {**os.environ, "PATH": str(bindir), "GH_ARGS": str(args)}
    return env, args


def test_fetch_updates_upstream_origin_and_coworker_remotes(repos):
    me = repos / "me"
    commit(repos / "seed", "B")
    git(repos / "seed", "push", "-q", "origin", "main")
    git(repos, "init", "-q", "--bare", "nishchay.git")
    git(me, "remote", "add", "nishchay", "../nishchay.git")
    out = run_script("forkflow-fetch", me)
    assert out.returncode == 0, out.stderr
    assert "fetching upstream/main" in out.stderr
    assert "fetching origin" in out.stderr
    assert "fetching mohit" in out.stderr
    assert "fetching nishchay" in out.stderr
    assert git(me, "log", "-1", "--format=%s", "upstream/main").stdout.strip() == "B"
    assert git(me, "log", "-1", "--format=%s", "mohit/feat").stdout.strip() == "b.py"


def test_borrow_one_file_stops_before_commit_and_does_not_push(repos):
    me = repos / "me"
    out = run_script("forkflow-borrow", me, "mohit/feat", "a.py")
    assert out.returncode == 0, out.stderr
    assert git(me, "branch", "--show-current").stdout.strip() == "borrow-mohit-feat"
    assert (me / "a.py").read_text() == "from mohit\n"
    assert not (me / "b.py").exists()
    status = git(me, "status", "--porcelain").stdout
    assert "a.py" in status and "b.py" not in status
    assert git(me, "log", "-1", "--format=%s").stdout.strip() == "A"
    assert "borrow-mohit-feat" not in git(repos, "--git-dir=fork.git", "branch").stdout


def test_borrow_starts_from_the_fetched_upstream_primary(repos):
    commit(repos / "seed", "C")
    git(repos / "seed", "push", "-q", "origin", "main")
    me = repos / "me"
    out = run_script("forkflow-borrow", me, "--commit", "-m", "borrow a.py", "mohit/feat", "a.py")
    assert out.returncode == 0, out.stderr
    assert git(me, "log", "--format=%s").stdout.splitlines()[:3] == ["borrow a.py", "C", "A"]


def test_borrow_sanitizes_a_slashed_branch_name(repos):
    mw = repos / "mohit-wt"
    git(mw, "checkout", "-q", "-b", "feature/foo")
    commit(mw, "a.py", "slashed\n")
    git(mw, "push", "-q", "fork", "feature/foo")
    me = repos / "me"
    out = run_script("forkflow-borrow", me, "mohit/feature/foo", "a.py")
    assert out.returncode == 0, out.stderr
    assert git(me, "branch", "--show-current").stdout.strip() == "borrow-mohit-feature-foo"
    assert (me / "a.py").read_text() == "slashed\n"


def test_borrow_commit_records_only_the_given_paths(repos):
    me = repos / "me"
    out = run_script("forkflow-borrow", me, "-b", "take-a", "--commit", "-m", "borrow a.py", "mohit/feat", "a.py")
    assert out.returncode == 0, out.stderr
    assert git(me, "branch", "--show-current").stdout.strip() == "take-a"
    assert git(me, "log", "-1", "--format=%s").stdout.strip() == "borrow a.py"
    assert git(me, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").stdout.strip() == "a.py"
    assert git(me, "status", "--porcelain").stdout == ""


def test_borrow_dry_run_does_not_touch_the_tree(repos):
    me = repos / "me"
    fetched = run_script("forkflow-fetch", me)
    assert fetched.returncode == 0, fetched.stderr
    before = git(me, "rev-parse", "mohit/feat").stdout
    head = git(me, "rev-parse", "HEAD").stdout
    branch = git(me, "branch", "--show-current").stdout
    status = git(me, "status", "--porcelain").stdout
    commit(repos / "mohit-wt", "a.py", "newer\n")
    git(repos / "mohit-wt", "push", "-q", "fork", "feat")
    out = run_script("forkflow-borrow", me, "--dry-run", "mohit/feat", "a.py")
    assert out.returncode == 0, out.stderr
    assert "git switch -c borrow-mohit-feat upstream/main" in out.stderr
    assert "stop before commit" in out.stderr
    assert "from mohit" in out.stdout
    assert "newer" not in out.stdout
    assert git(me, "rev-parse", "HEAD").stdout == head
    assert git(me, "branch", "--show-current").stdout == branch
    assert git(me, "status", "--porcelain").stdout == status
    assert git(me, "rev-parse", "mohit/feat").stdout == before
    assert "borrow-mohit-feat" not in git(me, "branch").stdout


def test_borrow_requires_a_path_and_a_clean_tracked_tree(repos):
    me = repos / "me"
    missing = run_script("forkflow-borrow", me, "mohit/feat")
    assert missing.returncode != 0 and "at least one path" in missing.stderr
    assert git(me, "branch", "--show-current").stdout.strip() == "main"
    (me / "A").write_text("dirty\n")
    dirty = run_script("forkflow-borrow", me, "--dry-run", "mohit/feat", "a.py")
    assert dirty.returncode != 0 and "tracked" in dirty.stderr
    assert git(me, "branch", "--show-current").stdout.strip() == "main"
    assert (me / "A").read_text() == "dirty\n"


def test_borrow_refuses_an_unknown_remote(repos):
    out = run_script("forkflow-borrow", repos / "me", "nobody/feat", "a.py")
    assert out.returncode != 0 and "no remote 'nobody'" in out.stderr


def test_pr_calls_gh_with_the_upstream_repo_and_the_fork_head(repos, tmp_path):
    me = repos / "me"
    git(me, "checkout", "-q", "-b", "feat")
    commit(me, "F", "f\n")
    git(me, "push", "-q", "-u", "origin", "feat")
    git(me, "remote", "set-url", "upstream", "https://github.com/unbxd/service.git")
    git(me, "remote", "set-url", "origin", "git@github.com:maaroofunbxd/service.git")
    env, args = fake_gh(tmp_path)
    out = run_script("forkflow-pr", me, "-t", "Take F", "-b", "Borrowed.", "--draft", env=env)
    assert out.returncode == 0, out.stderr
    assert args.read_text().splitlines() == [
        "pr", "create", "--repo", "unbxd/service", "--base", "main", "--head", "maaroofunbxd:feat",
        "--title", "Take F", "-b", "Borrowed.", "--draft",
    ]


def test_pr_refuses_without_gh_without_upstream_or_without_a_push(repos, tmp_path):
    me = repos / "me"
    bindir = tmp_path / "bin-no-gh"
    bindir.mkdir()
    os.symlink(shutil.which("git"), bindir / "git")
    os.symlink(shutil.which("bash"), bindir / "bash")
    no_gh = {**os.environ, "PATH": str(bindir)}
    out = run_script("forkflow-pr", me, "-t", "T", env=no_gh)
    assert out.returncode != 0 and "gh is not installed" in out.stderr

    git(me, "checkout", "-q", "-b", "feat")
    commit(me, "F", "f\n")
    env, args = fake_gh(tmp_path / "pushed")
    not_pushed = run_script("forkflow-pr", me, "-t", "T", env=env)
    assert not_pushed.returncode != 0 and "origin/feat doesn't exist" in not_pushed.stderr
    assert not args.exists()

    git(me, "push", "-q", "-u", "origin", "feat")
    commit(repos / "seed", "B")
    git(repos / "seed", "push", "-q", "origin", "main")
    git(me, "fetch", "-q", "upstream")
    behind = run_script("forkflow-pr", me, "-t", "T", env=env)
    assert behind.returncode != 0 and "git sync" in behind.stderr
    assert not args.exists()

    git(me, "remote", "remove", "upstream")
    no_up = run_script("forkflow-pr", me, "-t", "T", env=env)
    assert no_up.returncode != 0 and "no upstream remote" in no_up.stderr


def test_forkflow_entry_dispatches_fetch(repos):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
    out = subprocess.run(
        [sys.executable, "-c", "import sys; sys.argv = ['forkflow', 'fetch']; from forkflow.scripts import main; main()"],
        cwd=repos / "me", capture_output=True, text=True, env=env,
    )
    assert out.returncode == 0, out.stderr
    assert "[forkflow fetch]" in out.stderr
    assert "mohit/feat" in git(repos / "me", "branch", "-r").stdout
