from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import re


@dataclass(frozen=True)
class MeetingMetadata:
    """会議メタデータの値オブジェクト"""
    
    title: str
    date_time: Optional[datetime]
    web_view_link: str
    created_time: str
    modified_time: str
    owner_email: str
    invited_accounts: List[str]
    
    def __post_init__(self):
        if not self.title:
            raise ValueError("Meeting title cannot be empty")
        
        if not self.web_view_link:
            raise ValueError("Web view link cannot be empty")
        
        if not self.owner_email:
            raise ValueError("Owner email cannot be empty")
    
    @classmethod
    def from_google_doc_metadata(
        cls,
        name: str,
        web_view_link: str,
        created_time: str,
        modified_time: str,
        owners: List[Dict[str, Any]],
        invited_accounts: List[str] = None
    ) -> 'MeetingMetadata':
        """GoogleドキュメントのメタデータからMeetingMetadataを作成"""
        
        # 会議情報の解析（タイトル、日付、時刻）
        parsed_info = cls._parse_meeting_info(name)
        meeting_datetime = cls._parse_datetime(parsed_info)
        
        # オーナー情報の取得
        owner_email = owners[0]['emailAddress'] if owners else ""
        
        return cls(
            title=parsed_info.get('title', name),
            date_time=meeting_datetime,
            web_view_link=web_view_link,
            created_time=created_time,
            modified_time=modified_time,
            owner_email=owner_email,
            invited_accounts=invited_accounts or []
        )
    
    @staticmethod
    def _parse_meeting_info(filename: str) -> Dict[str, str]:
        """ドキュメント名から会議情報を抽出"""
        # Gemini による会議メモの典型的な命名規則
        pattern = r"^(?P<title>.+?)\s*-\s*(?P<date>\d{4}/\d{2}/\d{2})\s*(?P<time>\d{1,2}:\d{2})"
        match = re.search(pattern, filename)
        
        if match:
            return match.groupdict()
        
        # パターンにマッチしない場合はファイル名全体をタイトルとする
        return {'title': filename, 'date': None, 'time': None}
    
    @staticmethod
    def _parse_datetime(parsed_info: Dict[str, str]) -> Optional[datetime]:
        """日付と時刻の文字列からdatetimeオブジェクトを作成"""
        date_str = parsed_info.get('date')
        time_str = parsed_info.get('time')
        
        if not date_str or not time_str:
            return None
        
        try:
            datetime_str = f"{date_str} {time_str}"
            return datetime.strptime(datetime_str, "%Y/%m/%d %H:%M")
        except ValueError:
            return None
    
    def format_display_title(self) -> str:
        """表示用のタイトルを取得"""
        if self.date_time:
            return f"{self.title} ({self.date_time.strftime('%Y/%m/%d %H:%M')})"
        return self.title
    
    def is_recent(self, days: int = 30) -> bool:
        """指定日数以内の会議かどうか"""
        if not self.date_time:
            return False
        
        now = datetime.now()
        delta = now - self.date_time
        return delta.days <= days