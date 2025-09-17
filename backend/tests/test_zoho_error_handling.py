#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zoho書き込みエラーハンドリングのテスト

問題：
- 他の求職者はZoho書き込み成功するが、特定の候補者（西嶋 美沙）では書き込みが行われない
- ログでは「成功」と表示されるが、実際にはZoho上でレコードが更新されていない
- 原因：difficult_workフィールドが255文字制限を超過、HTTP 202でもエラーレスポンス

修正内容：
1. レスポンスボディのエラーチェック追加
2. フィールド長制限の自動切り詰め機能追加
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
import json

# パスを追加してappモジュールをインポート可能にする
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.infrastructure.zoho.client import ZohoWriteClient


class TestZohoErrorHandling(unittest.TestCase):
    """Zoho書き込みエラーハンドリングのテスト"""

    def setUp(self):
        """テストセットアップ"""
        # 設定モック
        with patch('app.infrastructure.zoho.client.get_settings') as mock_settings:
            mock_settings.return_value = Mock(
                zoho_client_id="test_client_id",
                zoho_client_secret="test_client_secret",
                zoho_refresh_token="test_refresh_token",
                zoho_accounts_base_url="https://accounts.zoho.com",
                zoho_api_base_url="https://www.zohoapis.com",
                zoho_app_hc_module="jobSeeker"
            )
            self.client = ZohoWriteClient()
            # アクセストークンを設定してAPI呼び出しをスキップ
            self.client._access_token = "test_token"
            self.client._token_expiry = 9999999999

    def test_field_length_truncation(self):
        """フィールド長制限の切り詰め機能テスト"""
        # 268文字のdifficult_workフィールド（実際のケース）
        long_difficult_work = '飛行機整備士の仕事での納期厳しさ、残業での徹夜の多さ。ユニクロで10年後、20年後に働いているイメージが湧かないこと。40歳になった時のタスク量や会社の求めるものと自身の働き方がマッチしないこと。周囲からのプレッシャーが増えていること。会社のトップが変わっても、時代の変化や働き方改革があっても、実際の社内慣習が変わらない点。「人に寄り添う」というやりがいが難しくなっている現状。日本事業の利益追求によるコストカット。人と関わる時間を減らせない中で、自身の仕事の技量を上げていくこととの両立が難しい。人材育成が会社として遅れていること。'

        # 長さを確認（268文字）
        self.assertEqual(len(long_difficult_work), 268)
        self.assertGreater(len(long_difficult_work), 255)

        structured_data = {
            "difficult_work": long_difficult_work,
            "enjoyed_work": "短いテキスト",
            "current_salary": 850
        }

        # 変換実行
        with patch('app.infrastructure.zoho.client.logger') as mock_logger:
            zoho_data = self.client._convert_structured_data_to_zoho(structured_data)

            # difficult_workが255文字に切り詰められていることを確認
            self.assertIn('difficult_work', zoho_data)
            self.assertLessEqual(len(zoho_data['difficult_work']), 255)
            self.assertEqual(zoho_data['difficult_work'], long_difficult_work[:255].rstrip())

            # 警告ログが出力されていることを確認
            mock_logger.warning.assert_called()
            warning_call = mock_logger.warning.call_args[0][0]
            self.assertIn('フィールド長制限適用', warning_call)
            self.assertIn('difficult_work', warning_call)
            self.assertIn('268文字 -> 255文字', warning_call)

            # 他のフィールドは影響なし
            self.assertEqual(zoho_data['enjoyed_work'], "短いテキスト")
            self.assertEqual(zoho_data['field28'], 850)  # current_salary -> field28

    def test_zoho_response_error_detection(self):
        """Zoho APIレスポンスエラー検出テスト（HTTP 202でもエラー含む場合）"""
        structured_data = {
            "difficult_work": "適切な長さのテキスト",
            "enjoyed_work": "テスト"
        }

        # HTTP 202だがエラーレスポンスの場合をモック（実際のケース）
        error_response = {
            'data': [
                {
                    'code': 'INVALID_DATA',
                    'details': {
                        'maximum_length': 255,
                        'api_name': 'difficult_work'
                    },
                    'message': 'invalid data',
                    'status': 'error'
                }
            ]
        }

        # urllib.request.urlopenをモック
        with patch('app.infrastructure.zoho.client.request.urlopen') as mock_urlopen:
            # レスポンスモック
            mock_response = MagicMock()
            mock_response.getcode.return_value = 202  # Accepted
            mock_response.read.return_value = json.dumps(error_response).encode('utf-8')
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            # 書き込み実行
            result = self.client.update_jobseeker_record(
                record_id="12522000004198855",
                structured_data=structured_data,
                skip_validation=True,  # バリデーションスキップ
                candidate_name="西嶋 美沙"
            )

            # エラーとして処理されることを確認
            self.assertEqual(result['status'], 'error')
            self.assertEqual(result['status_code'], 202)
            self.assertIn('INVALID_DATA', result['error'])
            self.assertIn('invalid data', result['error'])
            self.assertIn('maximum_length=255', result['error'])
            self.assertIn('api_name=difficult_work', result['error'])

    def test_zoho_response_success_detection(self):
        """Zoho APIレスポンス成功検出テスト（正常ケース）"""
        structured_data = {
            "difficult_work": "適切な長さのテキスト",
            "enjoyed_work": "テスト"
        }

        # 成功レスポンスの場合をモック
        success_response = {
            'data': [
                {
                    'code': 'SUCCESS',
                    'details': {
                        'Modified_Time': '2025-09-17T21:00:00+09:00',
                        'Modified_By': {
                            'name': 'Test User',
                            'id': '12345'
                        }
                    },
                    'message': 'record updated',
                    'status': 'success'
                }
            ]
        }

        # urllib.request.urlopenをモック
        with patch('app.infrastructure.zoho.client.request.urlopen') as mock_urlopen:
            # レスポンスモック
            mock_response = MagicMock()
            mock_response.getcode.return_value = 200
            mock_response.read.return_value = json.dumps(success_response).encode('utf-8')
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            # 書き込み実行
            result = self.client.update_jobseeker_record(
                record_id="12522000004198855",
                structured_data=structured_data,
                skip_validation=True,
                candidate_name="テスト候補者"
            )

            # 成功として処理されることを確認
            self.assertEqual(result['status'], 'success')
            self.assertEqual(result['status_code'], 200)
            self.assertIn('data', result)

    def test_mixed_response_with_errors(self):
        """複数レコードで一部エラーの場合のテスト"""
        structured_data = {"difficult_work": "テスト用の難しい仕事内容"}

        # 複数レコードで一部エラーのレスポンス
        mixed_response = {
            'data': [
                {
                    'code': 'SUCCESS',
                    'message': 'record updated',
                    'status': 'success'
                },
                {
                    'code': 'INVALID_DATA',
                    'details': {'field': 'difficult_work'},
                    'message': 'validation failed',
                    'status': 'error'
                }
            ]
        }

        with patch('app.infrastructure.zoho.client.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.getcode.return_value = 207  # Multi-Status
            mock_response.read.return_value = json.dumps(mixed_response).encode('utf-8')
            mock_response.__enter__ = Mock(return_value=mock_response)
            mock_response.__exit__ = Mock(return_value=None)
            mock_urlopen.return_value = mock_response

            # 書き込み実行
            result = self.client.update_jobseeker_record(
                record_id="test_id",
                structured_data=structured_data,
                skip_validation=True
            )

            # エラーとして処理されることを確認（一部でもエラーがあれば全体エラー）
            self.assertEqual(result['status'], 'error')
            self.assertIn('INVALID_DATA', result['error'])
            self.assertIn('validation failed', result['error'])


def main():
    """テスト実行関数"""
    print("=== Zoho書き込みエラーハンドリング テスト実行 ===")

    # 個別テスト実行
    suite = unittest.TestSuite()

    # 1. フィールド長制限テスト
    print("\n1. フィールド長制限の切り詰め機能テスト")
    suite.addTest(TestZohoErrorHandling('test_field_length_truncation'))

    # 2. エラーレスポンス検出テスト
    print("2. Zoho APIレスポンスエラー検出テスト")
    suite.addTest(TestZohoErrorHandling('test_zoho_response_error_detection'))

    # 3. 成功レスポンス検出テスト
    print("3. Zoho APIレスポンス成功検出テスト")
    suite.addTest(TestZohoErrorHandling('test_zoho_response_success_detection'))

    # 4. 混合レスポンステスト
    print("4. 複数レコード混合レスポンステスト")
    suite.addTest(TestZohoErrorHandling('test_mixed_response_with_errors'))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    if result.wasSuccessful():
        print("\n✅ すべてのテストが成功しました！")
        print("修正により以下の問題が解決されます：")
        print("- 長すぎるフィールドの自動切り詰め")
        print("- HTTP 202でもエラーレスポンスの適切な検出")
        print("- 実際のZoho書き込み失敗の適切なログ出力")
    else:
        print(f"\n❌ {len(result.failures + result.errors)}個のテストが失敗しました")
        for failure in result.failures + result.errors:
            print(f"  - {failure[0]}")

    return result.wasSuccessful()


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)