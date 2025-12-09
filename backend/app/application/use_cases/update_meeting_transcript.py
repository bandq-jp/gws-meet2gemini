from __future__ import annotations

import logging
from typing import Optional, Dict, Any

from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl
from app.infrastructure.supabase.repositories.structured_repository_impl import StructuredRepositoryImpl

logger = logging.getLogger(__name__)


class UpdateMeetingTranscriptUseCase:
    """議事録本文を上書きし、必要なら既存の構造化データを削除する"""

    def execute(
        self,
        meeting_id: str,
        text_content: str,
        transcript_provider: Optional[str] = None,
        delete_structured: bool = True,
    ) -> Dict[str, Any]:
        meetings = MeetingRepositoryImpl()
        structured_repo = StructuredRepositoryImpl()

        meeting = meetings.get_meeting(meeting_id)
        if not meeting:
            raise ValueError("meeting not found")

        updated = meetings.update_transcript(
            meeting_id=meeting_id,
            text_content=text_content,
            transcript_provider=transcript_provider,
        )

        if delete_structured:
            try:
                structured_repo.delete_by_meeting_id(meeting_id)
                logger.info("構造化データを削除しました: meeting_id=%s", meeting_id)
            except Exception as e:  # pragma: no cover
                logger.warning("構造化データ削除に失敗しました: meeting_id=%s error=%s", meeting_id, e)

        return updated or meeting
