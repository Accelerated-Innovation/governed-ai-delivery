"""A change cannot weaken existing tests, test support or other protected files.

The module under test is pure: the accepted `protected` declaration, every file
as it was at the comparison base and as it is now, and the paths that changed.
"""

from cli import protected_change as pc

DECLARED = {
    "tests": ["tests"],
    "files": ["tests/conftest.py", ".github/workflows", "known-failures.json"],
    "escape_markers": ["pytest.mark.skip", "@wip"],
}
TEST = "tests/test_routing.py"
BODY = "import routing\n\n\ndef test_routes():\n    assert routing.route(12000) == 'manager'\n"


def _assess(before: dict, after: dict, declared: dict = DECLARED) -> pc.Assessment:
    base = {path: text.encode() for path, text in before.items()}
    now = {path: text.encode() for path, text in after.items()}
    changed = sorted(p for p in base.keys() | now.keys() if base.get(p) != now.get(p))
    return pc.assess(declared, base, now, changed)


def _codes(assessment: pc.Assessment) -> list[tuple[str, str]]:
    return [(finding.code, finding.path) for finding in assessment.findings]


class TestExistingTests:
    def test_a_new_test_file_passes(self):
        assert (
            _assess(
                {TEST: BODY}, {TEST: BODY, "tests/test_new.py": "def test_x(): pass\n"}
            ).findings
            == ()
        )

    def test_a_test_added_to_an_existing_file_passes(self):
        added = "import other\n" + BODY + "\n\ndef test_more():\n    assert other.ok()\n"
        result = _assess({TEST: BODY}, {TEST: added})
        assert result.findings == () and result.checked == (TEST,)

    def test_a_changed_line_is_a_finding(self):
        result = _assess({TEST: BODY}, {TEST: BODY.replace("'manager'", "routing.route(12000)")})
        assert _codes(result) == [("test-altered", TEST)]
        assert "manager" not in result.findings[0].message

    def test_a_removed_line_is_a_finding(self):
        assert _codes(
            _assess({TEST: BODY}, {TEST: BODY.replace("    assert", "    pass  # assert")})
        ) == [("test-altered", TEST)]

    def test_reordered_lines_are_a_finding(self):
        two = "def test_a():\n    assert a\n\ndef test_b():\n    assert b\n"
        swapped = "def test_b():\n    assert b\n\ndef test_a():\n    assert a\n"
        assert _codes(_assess({TEST: two}, {TEST: swapped})) == [("test-altered", TEST)]

    def test_a_deleted_test_file_is_a_finding(self):
        assert _codes(_assess({TEST: BODY}, {})) == [("test-removed", TEST)]

    def test_line_endings_alone_are_not_a_change(self):
        assert _assess({TEST: BODY}, {TEST: BODY.replace("\n", "\r\n")}).findings == ()

    def test_a_file_that_is_not_text_must_be_identical(self):
        base = {"tests/data.bin": b"\xff\x00a"}
        result = pc.assess(
            DECLARED, base, {"tests/data.bin": b"\xff\x00a\nmore"}, ["tests/data.bin"]
        )
        assert _codes(result) == [("test-altered", "tests/data.bin")]

    def test_a_file_outside_the_declared_paths_is_not_assessed(self):
        result = _assess({"src/app.py": "a\n"}, {"src/app.py": "b\n"})
        assert (result.findings, result.checked) == ((), ())

    def test_a_folder_name_is_not_a_prefix_of_another(self):
        assert _assess({"tests_old/t.py": "a\n"}, {"tests_old/t.py": "b\n"}).checked == ()


class TestFiles:
    def test_any_change_to_an_existing_file_is_a_finding(self):
        path = ".github/workflows/ci.yml"
        added_only = _assess({path: "on: push\n"}, {path: "on: push\njobs: {}\n"})
        assert _codes(added_only) == [("protected-file-changed", path)]

    def test_a_deleted_file_is_a_finding(self):
        assert _codes(_assess({"known-failures.json": "{}"}, {})) == [
            ("protected-file-removed", "known-failures.json")
        ]

    def test_a_new_file_under_a_declared_folder_passes(self):
        assert _assess({}, {".github/workflows/new.yml": "on: push\n"}).findings == ()

    def test_a_path_under_both_follows_the_stricter_rule(self):
        path = "tests/conftest.py"
        result = _assess({path: "import pytest\n"}, {path: "import pytest\nimport os\n"})
        assert _codes(result) == [("protected-file-changed", path)]


class TestEscapeMarkers:
    FEATURE = "features/01_x/acceptance.feature"

    def test_a_marker_on_a_new_test_is_a_finding(self):
        added = BODY + "\n\n@pytest.mark.skip\ndef test_later():\n    assert False\n"
        result = _assess({TEST: BODY}, {TEST: added})
        assert _codes(result) == [("escape-marker-added", TEST)]
        assert "pytest.mark.skip" in result.findings[0].message

    def test_a_marker_in_a_new_file_is_a_finding(self):
        new = "tests/test_new.py"
        result = _assess({TEST: BODY}, {TEST: BODY, new: "@pytest.mark.skip\ndef test_x(): pass\n"})
        assert _codes(result) == [("escape-marker-added", new)]

    def test_a_marker_in_a_feature_definition_counts(self):
        base = "Feature: X\n\n  Scenario: A\n    Given a\n"
        added = base + "\n  @wip\n  Scenario: B\n    Given b\n"
        assert _codes(_assess({self.FEATURE: base}, {self.FEATURE: added})) == [
            ("escape-marker-added", self.FEATURE)
        ]

    def test_the_count_may_fall(self):
        """Removing the marker changes a line, which is its own finding; the count is not one."""
        marked = "@pytest.mark.skip\ndef test_a(): pass\n"
        result = _assess({TEST: marked}, {TEST: "def test_a(): pass\n"})
        assert _codes(result) == [("test-altered", TEST)]

    def test_only_a_rise_in_the_total_counts(self):
        """A marker that moves to a new file while its old file goes is not one more escape."""
        marked = "@pytest.mark.skip\ndef test_a(): pass\n"
        result = _assess({"tests/a.py": marked}, {"tests/b.py": marked})
        assert _codes(result) == [("test-removed", "tests/a.py")]

    def test_a_marker_outside_the_declared_tests_is_not_counted(self):
        assert _assess({}, {"src/app.py": "# pytest.mark.skip\n"}).findings == ()


class TestDeclaration:
    def test_an_empty_declaration_checks_nothing(self):
        result = pc.assess({}, {TEST: b"a"}, {TEST: b"b"}, [TEST])
        assert (result.findings, result.checked) == ((), ())

    def test_every_code_is_listed(self):
        assert pc.CODES == (
            "test-altered",
            "test-removed",
            "protected-file-changed",
            "protected-file-removed",
            "escape-marker-added",
        )
