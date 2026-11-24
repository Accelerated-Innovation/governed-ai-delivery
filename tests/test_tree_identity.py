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
    # A hook or shell may export these; they would redirect the command.
    inherited = {k: v for k, v in os.environ.items() if k not in ti._LOCATION_VARIABLES}
    environment = dict(
        inherited,
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


@pytest.fixture
def with_submodule(repo, tmp_path):
    library = tmp_path / "library"
    library.mkdir()
    _git(library, "init", "-q", "-b", "main")
    (library / "lib.py").write_text("v = 1\n", encoding="utf-8")
    _git(library, "add", "-A")
    _git(library, "commit", "-q", "-m", "lib one")
    _git(repo, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(library), "lib")
    _git(repo, "commit", "-q", "-m", "add lib")
    return repo


class TestSubmodules:
    """A dependency checked out inside the repository is part of what was tested."""

    def test_an_edit_inside_a_submodule_changes_the_digest(self, with_submodule):
        before = ti.observe(with_submodule)
        (with_submodule / "lib" / "lib.py").write_text("v = 2\n", encoding="utf-8")
        after = ti.observe(with_submodule)
        assert after.tree_digest != before.tree_digest
        assert after.clean is False

    def test_an_untracked_file_inside_a_submodule_changes_the_digest(self, with_submodule):
        before = ti.observe(with_submodule)
        (with_submodule / "lib" / "new.py").write_text("x = 1\n", encoding="utf-8")
        assert ti.observe(with_submodule).tree_digest != before.tree_digest

    def test_each_submodule_commit_has_its_own_digest(self, with_submodule):
        """The parent reports "modified" for any commit other than the recorded one,
        so the commit itself has to be part of the identity."""
        lib = with_submodule / "lib"
        digests = [ti.observe(with_submodule).tree_digest]
        for value in (2, 3):
            (lib / "lib.py").write_text(f"v = {value}\n", encoding="utf-8")
            _git(lib, "commit", "-q", "-am", f"lib {value}")
            digests.append(ti.observe(with_submodule).tree_digest)
        assert len(set(digests)) == 3

    def test_an_unchanged_submodule_is_clean_and_stable(self, with_submodule):
        first = ti.observe(with_submodule)
        assert first.clean is True
        assert ti.observe(with_submodule) == first

    def test_a_submodule_that_is_not_checked_out_is_still_identified(
        self, with_submodule, tmp_path
    ):
        clone = tmp_path / "clone"
        _git(tmp_path, "clone", "-q", str(with_submodule), str(clone))
        assert ti.observe(clone) == ti.observe(clone)


def test_inherited_git_location_variables_are_not_used(repo, tmp_path, monkeypatch):
    """A hook exports GIT_DIR and GIT_INDEX_FILE; they must not redirect the observation."""
    expected = ti.observe(repo)
    other = tmp_path / "other"
    other.mkdir()
    _git(other, "init", "-q", "-b", "main")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    monkeypatch.setenv("GIT_INDEX_FILE", str(other / ".git" / "index"))
    assert ti.observe(repo) == expected


def test_an_index_that_changes_during_the_observation_is_unavailable(repo, monkeypatch):
    real = ti._git
    calls = {"stage": 0}

    def staged_meanwhile(directory, *args):
        output = real(directory, *args)
        if args[:2] == ("ls-files", "--stage"):
            calls["stage"] += 1
            if calls["stage"] == 2:
                return output + b"changed"
        return output

    monkeypatch.setattr(ti, "_git", staged_meanwhile)
    with pytest.raises(ti.Unavailable) as error:
        ti.observe(repo)
    assert "changed while" in str(error.value)
