"""State definition for the self-improvement pipeline."""
from __future__ import annotations

from typing import Any, TypedDict

from tech_curation.feedback.parser import FeedbackItem


class SourceStats(TypedDict):
    source: str
    avg_relevance: float
    count: int


class TopicChanges(TypedDict):
    add: list[str]
    remove: list[str]


class ChangeProposal(TypedDict):
    param_changes: dict[str, float | int] | None
    prompt_changes: dict[str, str] | None
    topic_changes: TopicChanges | None
    reason: str


class ImproveState(TypedDict):
    note_path: str
    note_content: str
    feedback_items: list[FeedbackItem]
    overall_feedback: str       # <!-- overall: comment=... --> の内容
    policy: str                 # agent-config/policy.md の内容
    source_labels: list[str]
    source_stats: list[SourceStats]
    qualitative_analysis: str
    change_proposal: ChangeProposal | None
    proposal_review_issues: list[str]
    proposal_review_iterations: int
    errors: list[str]
