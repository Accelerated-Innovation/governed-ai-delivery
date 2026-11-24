"""The identity of a working tree: the commit and a digest of everything Git sees.

Results count only for the tree that produced them, so the digest must change
when a file Git sees changes, and must not change when a result file is written.
These tests use a real repository.
"""

import os
import subprocess
from pathlib import Path

import pytest

from cli import tree_identity as ti


def _git(repo: Path, *args: str) -> str:
    environment = dict(
        os.environ,
        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
        GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid",
        GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
    )  # fmt: skip
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True,
        env=environment,
    ).stdout.strip()  # fmt: skip


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    (root / "app.py").write_text("print('one')\n", encoding="utf-8")
    (root / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "first")
    return root


def test_identity_names_the_commit(repo):
    assert ti.observe(repo).commit == _git(repo, "rev-parse", "HEAD")


def test_the_same_tree_has_the_same_digest(repo):
    assert ti.observe(repo) == ti.observe(repo)


def test_a_clean_tree_is_reported_clean(repo):
    assert ti.observe(repo).clean is True


@pytest.mark.parametrize(
    "change",
    ["modify", "stage", "untracked", "delete", "mode", "untracked-content"],
)
def test_a_change_git_sees_changes_the_digest(repo, change):
    (repo / "notes.txt").write_text("a\n", encoding="utf-8")
    before = ti.observe(repo)
    if change == "modify":
        (repo / "app.py").write_text("print('two')\n", encoding="utf-8")
    elif change == "stage":
        (repo / "app.py").write_text("print('two')\n", encoding="utf-8")
        before = ti.observe(repo)
        _git(repo, "add", "app.py")
        (repo / "app.py").write_text("print('three')\n", encoding="utf-8")
    elif change == "untracked":
        (repo / "new.py").write_text("x = 1\n", encoding="utf-8")
    elif change == "delete":
        (repo / "app.py").unlink()
    elif change == "mode":
        (repo / "app.py").chmod(0o755)
    else:
        (repo / "notes.txt").write_text("b\n", encoding="utf-8")
    after = ti.observe(repo)
    assert after.tree_digest != before.tree_digest
    assert after.clean is False


def test_a_new_commit_changes_the_commit_and_the_digest(repo):
    before = ti.observe(repo)
    (repo / "app.py").write_text("print('two')\n", encoding="utf-8")
    _git(repo, "commit", "-q", "-am", "second")
    after = ti.observe(repo)
    assert after.commit != before.commit
    assert after.tree_digest != before.tree_digest


def test_reverting_an_edit_restores_the_digest(repo):
    before = ti.observe(repo)
    (repo / "app.py").write_text("print('two')\n", encoding="utf-8")
    (repo / "app.py").write_text("print('one')\n", encoding="utf-8")
    assert ti.observe(repo).tree_digest == before.tree_digest


def test_an_ignored_file_does_not_change_the_digest(repo):
    before = ti.observe(repo)
    (repo / "ignored").mkdir()
    (repo / "ignored" / "cache.bin").write_text("x", encoding="utf-8")
    assert ti.observe(repo).tree_digest == before.tree_digest


def test_an_excluded_path_does_not_change_the_digest(repo):
    """Writing the result files must not make their own results stale."""
    before = ti.observe(repo, exclude=("junit.xml", "reports/eval.json"))
    (repo / "junit.xml").write_text("<testsuite/>", encoding="utf-8")
    (repo / "reports").mkdir()
    (repo / "reports" / "eval.json").write_text("{}", encoding="utf-8")
    after = ti.observe(repo, exclude=("junit.xml", "reports/eval.json"))
    assert after.tree_digest == before.tree_digest
    assert ti.observe(repo).tree_digest != before.tree_digest


def test_a_tracked_excluded_path_does_not_change_the_digest_when_edited(repo):
    (repo / "junit.xml").write_text("<testsuite/>", encoding="utf-8")
    _git(repo, "add", "junit.xml")
    _git(repo, "commit", "-q", "-m", "tracked result")
    before = ti.observe(repo, exclude=("junit.xml",))
    (repo / "junit.xml").write_text("<testsuite tests='1'/>", encoding="utf-8")
    assert ti.observe(repo, exclude=("junit.xml",)).tree_digest == before.tree_digest


def test_a_target_below_the_repository_root_sees_the_whole_repository(repo):
    """A change in a shared directory outside the target still makes results stale."""
    service = repo / "services" / "api"
    service.mkdir(parents=True)
    (service / "main.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "service")
    before = ti.observe(service, exclude=("junit.xml",))
    (service / "junit.xml").write_text("<testsuite/>", encoding="utf-8")
    assert ti.observe(service, exclude=("junit.xml",)).tree_digest == before.tree_digest
    (repo / "app.py").write_text("print('two')\n", encoding="utf-8")
    assert ti.observe(service, exclude=("junit.xml",)).tree_digest != before.tree_digest


def test_observing_writes_nothing(repo):
    def snapshot():
        return {
            p.relative_to(repo).as_posix(): (p.stat().st_mtime_ns, p.stat().st_size)
            for p in repo.rglob("*")
            if p.is_file()
        }

    (repo / "app.py").write_text("print('two')\n", encoding="utf-8")
    before = snapshot()
    ti.observe(repo)
    assert snapshot() == before


def test_a_directory_that_is_not_a_repository_is_unavailable(tmp_path):
    with pytest.raises(ti.Unavailable):
        ti.observe(tmp_path)


def test_a_repository_with_no_commit_is_unavailable(tmp_path):
    _git(tmp_path, "init", "-q")
    with pytest.raises(ti.Unavailable):
        ti.observe(tmp_path)


def test_a_missing_git_is_unavailable(repo, monkeypatch):
    monkeypatch.setenv("PATH", "")
    with pytest.raises(ti.Unavailable):
        ti.observe(repo)
