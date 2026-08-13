"""The delivery-side evidence contract.

govkit already ships a rigorous evidence contract — but as an opt-in L5
extension governing the *customer's* runtime agents, so it never applies to
govkit's own delivery layer. Its decisive line:

    A producer self-check is advisory. The task owner never commits its own
    final gate.

The FIRST/Virtue prediction *is* a producer self-check used as a final gate.
This contract promotes that vocabulary to the delivery side rather than
inventing a parallel one, so the two cannot drift into different meanings for
the same words.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

CONTRACT_PATHS = [
    REPO_ROOT / "docs" / area / "evaluation" / "EVIDENCE_CONTRACT.md"
    for area in ("backend", "ui")
]

SOURCE_CONTRACT = (
    REPO_ROOT / "extensions" / "skill-oriented-agent-architecture" / "docs" / "backend"
    / "architecture" / "EVALUATION_EVIDENCE_AND_COMPLETION_CONTRACT.md"
)

REQUIRED_SECTIONS = [
    "## Separate concepts",
    "## Gate outcomes",
    "## What govkit measures today",
    "## Forecast versus evidence",
]

# The four outcomes, lifted verbatim from the source contract.
GATE_OUTCOMES = ["PASS", "FAIL", "INCONCLUSIVE", "ERROR"]


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def test_source_contract_still_says_what_we_are_lifting():
    """Guard the premise. If the extension contract changes its vocabulary, the
    delivery-side copy is no longer a promotion of it and must be revisited."""
    text = SOURCE_CONTRACT.read_text(encoding="utf-8")
    assert "A producer self-check is advisory" in text
    assert "never commits its own final gate" in text
    for outcome in GATE_OUTCOMES:
        assert f"`{outcome}`" in text, outcome


@pytest.mark.parametrize("path", CONTRACT_PATHS, ids=_rel)
def test_contract_exists_and_has_required_sections(path: Path):
    text = path.read_text(encoding="utf-8")
    missing = [s for s in REQUIRED_SECTIONS if s not in text]
    assert not missing, f"{_rel(path)} missing: {missing}"


@pytest.mark.parametrize("path", CONTRACT_PATHS, ids=_rel)
def test_contract_defines_all_four_gate_outcomes(path: Path):
    """INCONCLUSIVE is the one that matters: today an unmeasured dimension reads
    as green, which is why a fabricated score is indistinguishable from a
    verified one."""
    text = path.read_text(encoding="utf-8")
    missing = [o for o in GATE_OUTCOMES if o not in text]
    assert not missing, f"{_rel(path)} missing outcome(s): {missing}"


@pytest.mark.parametrize("path", CONTRACT_PATHS, ids=_rel)
def test_contract_states_inconclusive_is_not_a_pass(path: Path):
    text = path.read_text(encoding="utf-8").lower()
    assert "inconclusive is not a pass" in text, (
        f"{_rel(path)} must state plainly that an unmeasured dimension does not pass"
    )


@pytest.mark.parametrize("path", CONTRACT_PATHS, ids=_rel)
def test_contract_carries_the_producer_self_check_rule(path: Path):
    """The whole argument rests on this sentence; it must be quoted, not paraphrased."""
    text = path.read_text(encoding="utf-8")
    assert "producer self-check" in text, _rel(path)
    assert "never commits its own final gate" in text, _rel(path)


@pytest.mark.parametrize("path", CONTRACT_PATHS, ids=_rel)
def test_contract_cites_its_source(path: Path):
    """A promoted vocabulary must say where it came from, or the two copies drift
    into different meanings for the same words."""
    text = path.read_text(encoding="utf-8")
    assert "EVALUATION_EVIDENCE_AND_COMPLETION_CONTRACT.md" in text, _rel(path)


@pytest.mark.parametrize("path", CONTRACT_PATHS, ids=_rel)
def test_contract_is_honest_about_what_is_unmeasured(path: Path):
    """The point of this pass is visible gaps, not a claim of full coverage.
    'Clear' is irreducibly judgemental and must be named as such."""
    text = path.read_text(encoding="utf-8")
    assert "Clear" in text, _rel(path)
    assert re.search(r"judgement|judgemental|not mechanically", text, re.I), _rel(path)


def test_contract_body_is_identical_across_areas():
    """[[feedback_agent_parity]] applied to a governed doc: the vocabulary must
    mean the same thing in a backend repo and a UI one."""
    bodies = {p: p.read_text(encoding="utf-8") for p in CONTRACT_PATHS}
    assert len(set(bodies.values())) == 1, (
        "EVIDENCE_CONTRACT.md differs between areas: "
        f"{[_rel(p) for p in bodies]}"
    )
