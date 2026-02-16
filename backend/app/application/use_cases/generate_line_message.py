from __future__ import annotations
import logging
from typing import Any, Dict, List

from app.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)


class GenerateLineMessageUseCase:
    def __init__(self):
        self.gemini = GeminiClient(
            model="gemini-2.5-flash",
            temperature=0.7,
            max_tokens=1024,
        )

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._build_prompt(data)
        try:
            result = self.gemini.generate_content(
                prompt=prompt,
                response_mime_type="text/plain",
            )
            message = result.strip() if result else self._template_fallback(data)
        except Exception as e:
            logger.warning("[line_message] Gemini failed, using template: %s", e)
            message = self._template_fallback(data)

        return {"message": message, "char_count": len(message)}

    def _build_prompt(self, data: Dict[str, Any]) -> str:
        appeal = ", ".join(data.get("appeal_points", []))
        return f"""以下の求人情報をもとに、候補者に送るLINEメッセージを生成してください。

## ルール
- 候補者が「この求人について詳しく聞きたい」と思えるような、魅力的で親しみやすいメッセージ
- 300-500文字程度
- 候補者のファーストネームがあれば使う（「〜様」で呼びかける）
- 絵文字は適度に使用OK（多用しない）
- CAとして候補者に語りかけるトーン
- 具体的な年収金額は含めず「ご希望に沿った条件」等で表現
- 候補者の希望に寄り添った内容にする
- 最後に「ご興味ございましたらお気軽にお返事ください」的なCTA

## 求人情報
- 企業名: {data.get('company_name', '')}
- 求人名: {data.get('job_name', '')}
- 訴求ポイント: {appeal}
- 推薦理由: {data.get('recommendation_reason', '')}
- 勤務地: {data.get('location', '')}
- リモート: {data.get('remote', '')}

## 候補者情報
- 名前: {data.get('candidate_name', '')}
- 候補者の希望: {data.get('candidate_desires', '')}

メッセージ本文のみ出力してください（```やタイトルは不要）:"""

    def _template_fallback(self, data: Dict[str, Any]) -> str:
        name = data.get("candidate_name", "")
        name_line = f"{name}様\n\n" if name else ""
        company = data.get("company_name", "")
        points = data.get("appeal_points", [])
        points_text = "、".join(points[:3]) if points else "ご希望に合った条件"
        return (
            f"{name_line}"
            f"お世話になっております。\n"
            f"ご希望にマッチしそうな求人がございましたのでご連絡いたしました。\n\n"
            f"{company}のポジションで、{points_text}といった特徴がございます。\n\n"
            f"ご興味ございましたらお気軽にお返事ください。\n"
            f"詳細をご説明させていただきます。"
        )
