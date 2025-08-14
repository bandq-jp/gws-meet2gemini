"""
後方互換性のためのエイリアス

元のGeminiStructuredExtractorSplitクラスは新しいアーキテクチャに移行しました：
- app.infrastructure.gemini.structured_extractor.StructuredDataExtractor

このファイルは既存のインポートを壊さないための移行期間用エイリアスです。
"""

from app.infrastructure.gemini.structured_extractor import StructuredDataExtractor

# 後方互換性のためのエイリアス
GeminiStructuredExtractorSplit = StructuredDataExtractor