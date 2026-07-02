"""Tests for cli/marker.py — the _OneTimeWarning machinery.

MARKER_WARNING_CONSOLIDATION_PLAN.md increment 1. One value object owns the
fire-once / env-suppress / reset behavior that previously existed as three
copies of (global flag + env check + print + reset helper). The three
migration warnings' end-to-end behavior stays pinned by the existing
integration tests in test_govkit.py; these tests cover the machinery itself.
"""


class TestOneTimeWarning:
    ENV = "GOVKIT_TEST_WARNING"

    def _fresh(self):
        from cli.marker import _OneTimeWarning

        return _OneTimeWarning(self.ENV)

    def test_warn_prints_to_stderr_once(self, capsys, monkeypatch):
        monkeypatch.delenv(self.ENV, raising=False)
        w = self._fresh()
        w.warn("something happened")
        w.warn("something happened")
        assert capsys.readouterr().err.count("something happened") == 1

    def test_warn_suppressed_by_env_var(self, capsys, monkeypatch):
        monkeypatch.setenv(self.ENV, "1")
        w = self._fresh()
        w.warn("something happened")
        assert "something happened" not in capsys.readouterr().err

    def test_suppression_does_not_mark_printed(self, capsys, monkeypatch):
        """Matching the old globals: an env-suppressed call leaves the
        warning armed, so unsetting the env var later still lets it fire."""
        monkeypatch.setenv(self.ENV, "1")
        w = self._fresh()
        w.warn("something happened")
        monkeypatch.delenv(self.ENV)
        w.warn("something happened")
        assert capsys.readouterr().err.count("something happened") == 1

    def test_env_var_checked_at_warn_time(self, capsys, monkeypatch):
        """Instances are module-level and outlive test env changes — the
        env var must be read when warn() fires, not at construction."""
        monkeypatch.delenv(self.ENV, raising=False)
        w = self._fresh()
        monkeypatch.setenv(self.ENV, "1")
        w.warn("late suppression")
        assert "late suppression" not in capsys.readouterr().err

    def test_reset_rearms(self, capsys, monkeypatch):
        monkeypatch.delenv(self.ENV, raising=False)
        w = self._fresh()
        w.warn("again")
        w.reset()
        w.warn("again")
        assert capsys.readouterr().err.count("again") == 2
