"""Unit tests for the Jev judgment helpers."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from tech_curation import jev
from tech_curation.collect.state import CollectedItem

RUBRIC = "- 0: 無関係\n- 1: 少し関係\n- 2: 関係あり\n- 3: かなり関係\n- 4: 中心的"


def _item(title: str = "Go 1.25 の iter 解説") -> CollectedItem:
    return CollectedItem(
        id="t", title=title, url="https://example.com", source="zenn", published="",
        body="本文", relevance_score=0.0, summary="", content_type="", thumbnail="", topic="",
    )


def _response(score: float = 0.0, choice: str = "", noul: float = 0.0) -> MagicMock:
    resp = MagicMock()
    resp.scores = {"relevance": MagicMock(score=score)}
    resp.choices = {"topic": MagicMock(choice=choice)}
    resp.nouls = {"worth": MagicMock(noul=noul)}
    return resp


class TestParseRubric:
    def test_numbered_lines(self):
        assert jev.parse_rubric(RUBRIC) == ["無関係", "少し関係", "関係あり", "かなり関係", "中心的"]

    def test_ignores_non_list_lines(self):
        assert jev.parse_rubric("説明文\n- 低い\n- 高い\n") == ["低い", "高い"]


class TestNormalizeScore:
    def test_five_levels(self):
        assert jev.normalize_score(3.0, 5) == 0.75

    def test_clamped(self):
        assert jev.normalize_score(5.0, 5) == 1.0
        assert jev.normalize_score(-1.0, 5) == 0.0

    def test_degenerate_rubric(self):
        assert jev.normalize_score(0.0, 1) == jev.NEUTRAL


class TestJudgeRelevanceAndTopic:
    def test_success(self):
        client = MagicMock()
        client.system_one.return_value = _response(score=3.0, choice="Go")
        with patch.object(jev, "_client", return_value=client):
            relevance, topic = jev.judge_relevance_and_topic(_item(), ["Go", "トレンド"], RUBRIC)
        assert relevance == 0.75
        assert topic == "Go"
        questions = client.system_one.call_args.kwargs["questions"]
        assert set(questions["topic"].criteria) == {"Go", "トレンド"}
        assert len(questions["relevance"].criteria) == 5

    def test_failure_returns_neutral(self):
        client = MagicMock()
        client.system_one.side_effect = RuntimeError("down")
        with patch.object(jev, "_client", return_value=client):
            assert jev.judge_relevance_and_topic(_item(), ["Go"], RUBRIC) == (jev.NEUTRAL, None)


class TestJudgeWorth:
    def test_success(self):
        client = MagicMock()
        client.system_one.return_value = _response(noul=0.83)
        with patch.object(jev, "_client", return_value=client):
            assert jev.judge_worth(_item(), "要約する価値があるか") == 0.83

    def test_failure_returns_neutral(self):
        with patch.object(jev, "_client", side_effect=RuntimeError("no key")):
            assert jev.judge_worth(_item(), "要約する価値があるか") == jev.NEUTRAL
