"""In-memory store for pending ask_user question groups.

Each pending group holds an asyncio.Event that the tool function awaits.
When the user submits responses via the REST endpoint, the event is set
and the tool function resumes with the user's answers.
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QuestionItem:
    """A single question within a group."""
    id: str
    question: str
    question_type: str  # "choice" | "text" | "confirm"
    options: list[str]


@dataclass
class PendingQuestionGroup:
    """A group of questions sent together in one ask_user call."""
    group_id: str
    questions: list[QuestionItem]
    event: asyncio.Event = field(default_factory=asyncio.Event)
    responses: Optional[dict[str, str]] = None


class AskUserStore:
    def __init__(self) -> None:
        self._pending: dict[str, PendingQuestionGroup] = {}

    def create_question_group(
        self,
        questions: list[dict],
    ) -> PendingQuestionGroup:
        group_id = uuid.uuid4().hex[:12]
        items = [
            QuestionItem(
                id=q.get("id", uuid.uuid4().hex[:8]),
                question=q["question"],
                question_type=q.get("type", "text"),
                options=q.get("options", []),
            )
            for q in questions
        ]
        pg = PendingQuestionGroup(group_id=group_id, questions=items)
        self._pending[group_id] = pg
        return pg

    def submit_responses(self, group_id: str, responses: dict[str, str]) -> bool:
        pg = self._pending.get(group_id)
        if pg is None:
            return False
        pg.responses = responses
        pg.event.set()
        return True

    def cleanup(self, group_id: str) -> None:
        self._pending.pop(group_id, None)


# Module-level singleton
ask_user_store = AskUserStore()
