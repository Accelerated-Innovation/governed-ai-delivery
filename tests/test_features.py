"""Tests for cli/features.py — the shared definition of "starter feature".

One owner for the fact "which features/ subdirectories are govkit's starters,
not the team's features". validate and upgrade both consume it; cmd_init
generates names inside the same grammar (starter_{slug}, starter_{slug}_l5).
"""

from cli.features import is_starter_feature, list_user_features


class TestIsStarterFeature:
    def test_bundled_starter_names_match(self):
        assert is_starter_feature("starter_backend")
        assert is_starter_feature("starter_backend_l5")

    def test_grammar_is_open(self):
        # cmd_init derives starter_{slug}[_l5] for any slug, so the predicate
        # must accept starters that don't exist yet.
        assert is_starter_feature("starter_data_l5")
        assert is_starter_feature("starter_custom")

    def test_user_feature_names_do_not_match(self):
        assert not is_starter_feature("my_feature")
        assert not is_starter_feature("starterkit")
        assert not is_starter_feature("restarter_backend")


class TestListUserFeatures:
    def test_excludes_starters_dotdirs_and_files(self, tmp_path):
        features = tmp_path / "features"
        (features / "alpha").mkdir(parents=True)
        (features / "starter_backend").mkdir()
        (features / "starter_custom").mkdir()
        (features / ".hidden").mkdir()
        (features / "notes.md").write_text("not a feature dir", encoding="utf-8")
        assert [p.name for p in list_user_features(features)] == ["alpha"]

    def test_sorted_by_name(self, tmp_path):
        features = tmp_path / "features"
        for name in ("zeta", "alpha", "mid"):
            (features / name).mkdir(parents=True)
        assert [p.name for p in list_user_features(features)] == ["alpha", "mid", "zeta"]

    def test_missing_dir_returns_empty(self, tmp_path):
        assert list_user_features(tmp_path / "features") == []


class TestBundledStarterGrammar:
    def test_every_bundled_starter_matches_the_grammar(self):
        """Every starter govkit ships must satisfy the shared predicate, so
        validate/upgrade exclude it in a target. Replaces the retired STARTERS
        set-coverage guard — the open grammar cannot go stale the way the
        closed set did when starter_data was added. Bundled features/ also
        holds repo-side worked examples (schema_contract_example etc.); those
        never install into targets and are outside this invariant."""
        from cli import paths

        starters = [
            p.name
            for p in (paths.REPO_ROOT / "features").iterdir()
            if p.is_dir() and p.name.startswith("starter")
        ]
        assert starters, "no bundled starters found — REPO_ROOT misresolved?"
        assert all(is_starter_feature(n) for n in starters), (
            f"bundled starter outside the grammar: "
            f"{[n for n in starters if not is_starter_feature(n)]}"
        )
