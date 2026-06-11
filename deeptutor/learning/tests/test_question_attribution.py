"""Tests for per-question knowledge point attribution.

The capability maps each generated question to a knowledge point via
``MasteryPathCapability._attribute_kps``. Question IDs are derived internally
from each item (``question_id``/``id`` key, else ``<prefix>_<index>``) rather
than supplied by the caller. LLM-supplied labels (id or name) win; any
un-attributed question is distributed round-robin across the module's KPs so
attribution does not bias toward the first KP.
"""

from deeptutor.capabilities.mastery_path import MasteryPathCapability
from deeptutor.learning.models import KnowledgePoint, KnowledgeType


def _kp(kp_id: str, name: str) -> KnowledgePoint:
    return KnowledgePoint(id=kp_id, name=name, type=KnowledgeType.CONCEPT, module_id="m1")


def test_attribute_kps_accepts_ids_and_names():
    kps = [_kp("kp1", "Limits"), _kp("kp2", "Derivatives")]
    data = {
        "questions": [
            {"knowledge_point_id": "kp2"},
            {"knowledge_point": "Limits"},
        ]
    }

    result = MasteryPathCapability._attribute_kps(data, kps, "quiz")

    # qids are derived as "<prefix>_<index>" since no id/question_id is present.
    assert result == {"quiz_0": "kp2", "quiz_1": "kp1"}


def test_attribute_kps_round_robins_missing_attribution():
    kps = [_kp("kp1", "Limits"), _kp("kp2", "Derivatives")]
    data = {"questions": [{}, {}, {}]}

    result = MasteryPathCapability._attribute_kps(data, kps, "quiz")

    assert result == {"quiz_0": "kp1", "quiz_1": "kp2", "quiz_2": "kp1"}


def test_attribute_kps_uses_explicit_question_ids():
    kps = [_kp("kp1", "Limits"), _kp("kp2", "Derivatives")]
    data = {
        "questions": [
            {"question_id": "qA", "knowledge_point_id": "kp1"},
            {"id": "qB", "knowledge_point": "Derivatives"},
        ]
    }

    result = MasteryPathCapability._attribute_kps(data, kps, "quiz")

    assert result == {"qA": "kp1", "qB": "kp2"}


def test_attribute_kps_mixes_labels_and_round_robin_fallback():
    kps = [_kp("kp1", "Limits"), _kp("kp2", "Derivatives")]
    # Middle question carries an explicit label; the others fall back to
    # round-robin keyed on positional index (i % len(kps)).
    data = {"questions": [{}, {"knowledge_point": "Limits"}, {}]}

    result = MasteryPathCapability._attribute_kps(data, kps, "quiz")

    assert result == {"quiz_0": "kp1", "quiz_1": "kp1", "quiz_2": "kp1"}


def test_attribute_kps_supports_exercises_key():
    kps = [_kp("kp1", "Limits"), _kp("kp2", "Derivatives")]
    data = {"exercises": [{"kp": "kp2"}, {"kp_id": "kp1"}]}

    result = MasteryPathCapability._attribute_kps(data, kps, "ex")

    assert result == {"ex_0": "kp2", "ex_1": "kp1"}


def test_attribute_kps_unknown_label_falls_back_to_round_robin():
    kps = [_kp("kp1", "Limits"), _kp("kp2", "Derivatives")]
    # An unrecognized label cannot resolve; it falls back to round-robin.
    data = {"questions": [{"knowledge_point": "Topology"}]}

    result = MasteryPathCapability._attribute_kps(data, kps, "quiz")

    assert result == {"quiz_0": "kp1"}


def test_attribute_kps_no_kps_yields_empty_ids():
    data = {"questions": [{"knowledge_point_id": "kp1"}, {}]}

    result = MasteryPathCapability._attribute_kps(data, [], "quiz")

    # With no module KPs, nothing can be attributed and round-robin is skipped.
    assert result == {"quiz_0": "", "quiz_1": ""}
