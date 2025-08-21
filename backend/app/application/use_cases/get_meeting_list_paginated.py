from __future__ import annotations
from typing import List, Optional, Dict, Any

from app.infrastructure.supabase.repositories.meeting_repository_impl import MeetingRepositoryImpl

class GetMeetingListPaginatedUseCase:
    """ページネーション付き議事録一覧取得ユースケース"""
    
    async def execute(
        self,
        page: int = 1,
        page_size: int = 40,
        accounts: Optional[List[str]] = None,
        structured: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        軽量な議事録一覧をページネーション付きで取得
        
        Args:
            page: ページ番号（1から開始）
            page_size: 1ページあたりのアイテム数（最大40）
            accounts: フィルタ対象のアカウント一覧
            structured: 構造化済みフィルタ（True: 構造化済みのみ, False: 未構造化のみ, None: すべて）
            
        Returns:
            ページネーション情報を含む議事録一覧
        """
        # ページサイズを制限
        if page_size > 40:
            page_size = 40
        if page < 1:
            page = 1
            
        repo = MeetingRepositoryImpl()
        return repo.list_meetings_paginated(
            page=page,
            page_size=page_size,
            accounts=accounts,
            structured=structured
        )