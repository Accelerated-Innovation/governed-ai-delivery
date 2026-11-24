"""The evaluation results file, and the criterion fields that go with it.

A measured score reaches `govkit evidence` through a small JSON file the
project's evaluation run writes. GovKit reads it and starts nothing.
"""

import json
import os
from pathlib import Path

import pytest
import yaml

from cli import criterion_identity, evaluation_results, paths
from cli.scenario_identity import IdentityError
from cli.schema_validation import DocumentError, validate_document

REQUIREMENT = "07_invoice_approval#evaluation:faithfulness"
BACKEND_SCHEMA = "backend/schemas/eval_criteria.schema.json"


def _write(tmp_path: Path, results, name: str = "govkit-eval-results.json", **extra) -> Path:
    path = tmp_path / name
    path.parent.mkdir(parents=True, exist_ok=True)
    document = {"schema_version": 1, "kind": "govkit.evaluation-results", "results": results}
    document.update(extra)
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _read(tmp_path: Path):
    files, error = evaluation_results.read_results(tmp_path)
    assert error is None, error
    return files


class TestReading:
    def test_no_file_is_no_results_and_no_error(self, tmp_path):
        assert _read(tmp_path) == []

    def test_a_measurement_is_read_with_its_optional_fields(self, tmp_path):
        _write(
            tmp_path,
            [{"requirement_id": REQUIREMENT, "value": 0.91, "unit": "ratio",
              "metric": "faithfulness", "n": 50}],
            tool="deepeval",
        )  # fmt: skip
        (result,) = _read(tmp_path)[0].results
        assert (result.requirement_id, result.value, result.unit, result.metric, result.n) == (
            REQUIREMENT, 0.91, "ratio", "faithfulness", 50,
        )  # fmt: skip
        assert result.errored is False
        assert result.source == "govkit-eval-results.json"

    def test_a_value_alone_is_enough(self, tmp_path):
        _write(tmp_path, [{"requirement_id": REQUIREMENT, "value": 1}])
        (result,) = _read(tmp_path)[0].results
        assert (result.value, result.unit, result.metric, result.n) == (1.0, None, None, None)

    def test_an_evaluation_that_errored_has_no_value(self, tmp_path):
        _write(tmp_path, [{"requirement_id": REQUIREMENT, "error": "judge timed out"}])
        (result,) = _read(tmp_path)[0].results
        assert result.errored is True and result.value is None

    def test_files_are_found_in_subdirectories_and_carry_a_digest(self, tmp_path):
        import hashlib

        path = _write(tmp_path, [], name="reports/govkit-eval-results-llm.json")
        (found,) = _read(tmp_path)
        assert found.path == "reports/govkit-eval-results-llm.json"
        assert found.content_digest == hashlib.sha256(path.read_bytes()).hexdigest()

    def test_another_tools_results_file_is_not_read(self, tmp_path):
        (tmp_path / "results.json").write_text("{}", encoding="utf-8")
        (tmp_path / "eval-results.json").write_text("{}", encoding="utf-8")
        assert _read(tmp_path) == []


class TestRefusal:
    """A results file that cannot be trusted stops the report; it is never read as empty."""

    def _error(self, tmp_path) -> str:
        files, error = evaluation_results.read_results(tmp_path)
        assert files is None
        return error

    def test_text_that_is_not_json(self, tmp_path):
        (tmp_path / "govkit-eval-results.json").write_text("{not json", encoding="utf-8")
        assert "govkit-eval-results.json" in self._error(tmp_path)

    @pytest.mark.parametrize(
        "result, why",
        [
            ({"requirement_id": REQUIREMENT}, "neither a value nor an error"),
            ({"requirement_id": REQUIREMENT, "value": 0.9, "error": "x"}, "both"),
            ({"requirement_id": REQUIREMENT, "value": "0.9"}, "value is text"),
            ({"requirement_id": REQUIREMENT, "value": True}, "value is a boolean"),
            ({"requirement_id": REQUIREMENT, "value": 0.9, "unit": "ms"}, "unknown unit"),
            ({"requirement_id": REQUIREMENT, "value": 0.9, "n": 0}, "empty sample"),
            ({"requirement_id": REQUIREMENT, "value": 0.9, "passed": True}, "unknown field"),
            ({"requirement_id": "faithfulness", "value": 0.9}, "not an identifier"),
            ({"value": 0.9}, "no identifier"),
        ],
        ids=lambda v: v if isinstance(v, str) else None,
    )
    def test_an_entry_the_schema_rejects(self, tmp_path, result, why):
        _write(tmp_path, [result])
        assert "govkit-eval-results.json" in self._error(tmp_path), why

    def test_a_wrong_kind(self, tmp_path):
        path = _write(tmp_path, [])
        path.write_text(path.read_text().replace("govkit.evaluation-results", "other"), "utf-8")
        assert self._error(tmp_path)

    def test_a_file_over_the_size_limit(self, tmp_path):
        path = _write(tmp_path, [])
        path.write_text(" " * (evaluation_results.MAX_BYTES + 1), encoding="utf-8")
        assert "larger" in self._error(tmp_path)

    def test_a_symbolic_link_is_not_followed(self, tmp_path):
        real = _write(tmp_path, [], name="elsewhere.json")
        (tmp_path / "govkit-eval-results.json").symlink_to(real)
        assert "symbolic link" in self._error(tmp_path)

    def test_a_value_that_is_not_finite(self, tmp_path):
        (tmp_path / "govkit-eval-results.json").write_text(
            '{"schema_version": 1, "kind": "govkit.evaluation-results", "results": '
            f'[{{"requirement_id": "{REQUIREMENT}", "value": NaN}}]}}',
            encoding="utf-8",
        )
        assert self._error(tmp_path)


class TestBundledContract:
    def test_the_units_are_the_ones_a_target_may_use(self):
        schema = json.loads(
            (paths.GOVERNANCE_DIR / "schemas/evaluation-results.schema.json").read_text("utf-8")
        )
        units = schema["$defs"]["result"]["properties"]["unit"]["enum"]
        assert tuple(units) == criterion_identity.UNITS

    def test_the_bundled_example_validates(self):
        example = paths.GOVERNANCE_DIR / "examples/evidence-report/evaluation-run.json"
        validate_document(json.loads(example.read_text("utf-8")), evaluation_results.SCHEMA)

    def test_the_bundled_example_criteria_validate(self):
        from jsonschema import Draft202012Validator

        schema = json.loads((paths.GOVERNANCE_DIR / BACKEND_SCHEMA).read_text("utf-8"))
        example = paths.GOVERNANCE_DIR / "examples/evidence-report/eval_criteria.yaml"
        document = yaml.safe_load(example.read_text("utf-8"))
        assert not list(Draft202012Validator(schema).iter_errors(document))

    def test_the_bundled_example_is_not_discovered_as_a_result(self):
        assert _read(paths.GOVERNANCE_DIR / "examples/evidence-report") == []


class TestCriterionSchema:
    """`target` and `execution_class` on a backend criterion."""

    BASE = {
        "version": 1,
        "mode": "llm",
        "unit_tests": {"enforce_FIRST": True, "minimum_FIRST_average": 4.0},
        "code_quality": {"enforce_virtues": True, "minimum_virtue_average": 4.0},
    }

    def _document(self, **criterion):
        item = {"name": "faithfulness", "eval_class": "custom", "threshold": 0.8,
                "fail_on": "below_threshold", **criterion}  # fmt: skip
        return {**self.BASE, "llm_evaluation": {"criteria": [item]}}

    def _schema(self):
        from jsonschema import Draft202012Validator

        return Draft202012Validator(
            json.loads((paths.GOVERNANCE_DIR / BACKEND_SCHEMA).read_text("utf-8"))
        )

    def test_a_criterion_without_the_new_fields_stays_valid(self):
        assert not list(self._schema().iter_errors(self._document()))

    @pytest.mark.parametrize("comparator", criterion_identity.COMPARATORS)
    def test_a_target_validates(self, comparator):
        target = {"metric": "m", "comparator": comparator, "value": 0.2, "unit": "ratio"}
        if comparator == "between":
            target["value_high"] = 0.4
        assert not list(self._schema().iter_errors(self._document(target=target)))

    @pytest.mark.parametrize(
        "target",
        [
            {"metric": "m", "comparator": ">", "value": 1, "unit": "ratio"},
            {"metric": "m", "comparator": ">=", "value": 1, "unit": "ms"},
            {"metric": "m", "comparator": ">=", "value": "1", "unit": "ratio"},
            {"metric": "", "comparator": ">=", "value": 1, "unit": "ratio"},
            {"comparator": ">=", "value": 1, "unit": "ratio"},
            {"metric": "m", "comparator": "between", "value": 1, "unit": "ratio"},
        ],
    )
    def test_a_target_the_graph_would_refuse_is_invalid(self, target):
        assert list(self._schema().iter_errors(self._document(target=target)))
        with pytest.raises(IdentityError):
            criterion_identity.read_criteria("p", self._document(target=target), "0" * 64)

    def test_the_schema_is_stricter_than_the_reader_about_unknown_keys(self):
        """The reader is as lenient as the graph; the schema is GovKit's gate."""
        target = {"metric": "m", "comparator": ">=", "value": 1, "unit": "ratio", "extra": 1}
        assert list(self._schema().iter_errors(self._document(target=target)))
        assert criterion_identity.read_criteria("p", self._document(target=target), "0" * 64)

    @pytest.mark.parametrize("value", criterion_identity.EXECUTION_CLASSES)
    def test_an_execution_class_validates(self, value):
        assert not list(self._schema().iter_errors(self._document(execution_class=value)))

    def test_an_unknown_execution_class_is_invalid(self):
        assert list(self._schema().iter_errors(self._document(execution_class="expensive")))

    def test_the_schema_and_the_reader_agree_on_the_closed_sets(self):
        criterion = json.loads((paths.GOVERNANCE_DIR / BACKEND_SCHEMA).read_text("utf-8"))["$defs"][
            "criterion"
        ]["properties"]
        assert tuple(criterion["execution_class"]["enum"]) == criterion_identity.EXECUTION_CLASSES
        target = criterion["target"]["properties"]
        assert tuple(target["comparator"]["enum"]) == criterion_identity.COMPARATORS
        assert tuple(target["unit"]["enum"]) == criterion_identity.UNITS

    def test_every_shipped_backend_criteria_file_still_validates(self):
        schema = self._schema()
        checked = 0
        for path in sorted((paths.REPO_ROOT / "features").glob("*/eval_criteria.yaml")):
            document = yaml.safe_load(path.read_text("utf-8"))
            if document.get("mode") in ("llm", "deterministic") and "unit_tests" in document:
                assert not list(schema.iter_errors(document)), path
                checked += 1
        assert checked


def test_document_error_is_what_validation_raises():
    with pytest.raises(DocumentError):
        validate_document({"kind": "nope"}, evaluation_results.SCHEMA)


class TestReviewCases:
    def _error(self, tmp_path) -> str:
        files, error = evaluation_results.read_results(tmp_path)
        assert files is None
        return error

    def test_a_duplicate_key_is_refused_not_resolved(self, tmp_path):
        """`json.loads` keeps the last of two keys, which would drop a failing result."""
        failing = f'[{{"requirement_id": "{REQUIREMENT}", "value": 0.1}}]'
        passing = f'[{{"requirement_id": "{REQUIREMENT}", "value": 0.9}}]'
        (tmp_path / "govkit-eval-results.json").write_text(
            '{"schema_version": 1, "kind": "govkit.evaluation-results", '
            f'"results": {failing}, "results": {passing}}}',
            encoding="utf-8",
        )
        assert "duplicate" in self._error(tmp_path)

    def test_a_duplicate_key_inside_a_result_is_refused(self, tmp_path):
        (tmp_path / "govkit-eval-results.json").write_text(
            '{"schema_version": 1, "kind": "govkit.evaluation-results", "results": '
            f'[{{"requirement_id": "{REQUIREMENT}", "value": 0.1, "value": 0.9}}]}}',
            encoding="utf-8",
        )
        assert "duplicate" in self._error(tmp_path)

    def test_a_value_too_large_for_a_float_is_refused_not_raised(self, tmp_path):
        (tmp_path / "govkit-eval-results.json").write_text(
            '{"schema_version": 1, "kind": "govkit.evaluation-results", "results": '
            f'[{{"requirement_id": "{REQUIREMENT}", "value": 1{"0" * 400}}}]}}',
            encoding="utf-8",
        )
        assert "govkit-eval-results.json" in self._error(tmp_path)

    @pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="needs named pipes")
    def test_a_file_that_is_not_regular_is_refused_without_opening_it(self, tmp_path):
        os.mkfifo(tmp_path / "govkit-eval-results.json")
        assert "not a regular file" in self._error(tmp_path)

    def test_a_link_is_refused_before_its_destination_is_examined(self, tmp_path):
        (tmp_path / "govkit-eval-results.json").symlink_to(tmp_path / "missing" / "nowhere.json")
        assert "symbolic link" in self._error(tmp_path)

    def test_a_long_metric_is_valid_in_both_contracts(self, tmp_path):
        """A result must repeat the target's metric, so the limits cannot differ."""
        metric = "m" * 300
        _write(tmp_path, [{"requirement_id": REQUIREMENT, "value": 1, "metric": metric}])
        assert _read(tmp_path)[0].results[0].metric == metric
        target = {"metric": metric, "comparator": ">=", "value": 1, "unit": "ratio"}
        document = TestCriterionSchema()._document(target=target)
        assert not list(TestCriterionSchema()._schema().iter_errors(document))


class TestCheckedHandle:
    """The file that was checked is the file that is read."""

    def test_the_limit_holds_when_the_file_grows_after_it_was_examined(self, tmp_path, monkeypatch):
        path = _write(tmp_path, [])
        real = os.fstat

        def grown(descriptor):
            # After the size check: the file is enlarged before it is read.
            status = real(descriptor)
            if not getattr(grown, "done", False):
                grown.done = True
                with open(path, "ab") as handle:
                    handle.write(b" " * (evaluation_results.MAX_BYTES + 1))
            return status

        monkeypatch.setattr(evaluation_results.os, "fstat", grown)
        files, error = evaluation_results.read_results(tmp_path)
        assert files is None and "larger" in error

    @pytest.mark.skipif(not hasattr(os, "O_NOFOLLOW"), reason="needs O_NOFOLLOW")
    def test_a_link_swapped_in_after_the_check_is_not_followed(self, tmp_path, monkeypatch):
        path = _write(tmp_path, [])
        elsewhere = _write(
            tmp_path, [{"requirement_id": REQUIREMENT, "value": 1}], name="other.json"
        )
        real = os.open

        def swapped(name, flags, *args, **kwargs):
            # Between the examination and the open: the file becomes a link.
            if str(name) == str(path) and not getattr(swapped, "done", False):
                swapped.done = True
                path.unlink()
                path.symlink_to(elsewhere)
            return real(name, flags, *args, **kwargs)

        monkeypatch.setattr(evaluation_results.os, "open", swapped)
        files, error = evaluation_results.read_results(tmp_path)
        assert files is None, files
        assert "govkit-eval-results.json" in error


class TestWithoutNoFollow:
    """Where the platform cannot refuse a link at open, the handle is compared
    with the path afterwards and a mismatch is refused."""

    def test_a_swapped_link_is_refused_without_o_nofollow(self, tmp_path, monkeypatch):
        path = _write(tmp_path, [])
        elsewhere = _write(
            tmp_path, [{"requirement_id": REQUIREMENT, "value": 1}], name="other.json"
        )
        real = os.open

        def swapped(name, flags, *args, **kwargs):
            if str(name) == str(path) and not getattr(swapped, "done", False):
                swapped.done = True
                path.unlink()
                path.symlink_to(elsewhere)
            return real(name, flags, *args, **kwargs)

        monkeypatch.delattr(evaluation_results.os, "O_NOFOLLOW", raising=False)
        monkeypatch.setattr(evaluation_results.os, "open", swapped)
        files, error = evaluation_results.read_results(tmp_path)
        assert files is None, files
        assert "changed while it was being read" in error

    def test_an_ordinary_file_is_still_read_without_o_nofollow(self, tmp_path, monkeypatch):
        _write(tmp_path, [{"requirement_id": REQUIREMENT, "value": 1}])
        monkeypatch.delattr(evaluation_results.os, "O_NOFOLLOW", raising=False)
        assert len(_read(tmp_path)[0].results) == 1

    def test_an_oversized_file_is_refused_before_it_is_opened(self, tmp_path, monkeypatch):
        path = _write(tmp_path, [])
        path.write_text(" " * (evaluation_results.MAX_BYTES + 1), encoding="utf-8")

        def never(*args, **kwargs):
            raise AssertionError("the file was opened")

        monkeypatch.setattr(evaluation_results.os, "open", never)
        files, error = evaluation_results.read_results(tmp_path)
        assert files is None and "larger" in error
