#!/usr/bin/env python3
"""Zoho書き込み詳細調査スクリプト"""

from app.infrastructure.zoho.client import ZohoWriteClient, ZohoClient
import time

def main():
    print('=== Zoho API権限・レスポンス詳細調査 ===')
    print()

    try:
        # 実際の書き込みデータを確認
        client = ZohoWriteClient()
        
        # テスト用の最小限データで試してみる
        timestamp = str(int(time.time()))[-6:]
        test_data = {
            'transfer_activity_status': f'テスト書き込み - {timestamp}'
        }
        
        print('📋 テスト用データで書き込み実行:')
        print(f'   データ: {test_data}')
        print()
        
        record_id = '12522000003710687'
        candidate_name = '佐藤 花子'
        
        # skip_validation=True で書き込み（バリデーションスキップして権限問題を調査）
        result = client.update_jobseeker_record(
            record_id=record_id, 
            structured_data=test_data,
            skip_validation=True,
            candidate_name=candidate_name
        )
        
        print('📊 書き込み結果:')
        print(f'   ステータス: {result.get("status")}')
        print(f'   HTTPコード: {result.get("status_code")}')
        
        if 'data' in result:
            zoho_response = result['data']
            print(f'   Zoho応答構造: {type(zoho_response)}')
            
            if zoho_response and isinstance(zoho_response, dict) and 'data' in zoho_response:
                print('   応答データ詳細:')
                for i, item in enumerate(zoho_response['data']):
                    print(f'     レコード{i+1}:')
                    for key, value in item.items():
                        print(f'       {key}: {value}')
            else:
                print(f'   Zoho応答全体: {zoho_response}')
        
        if result.get('status') != 'success':
            print(f'   エラー: {result.get("error")}')
        else:
            print('✅ API呼び出しは成功しました')
            
            # 書き込み後に実際の値を確認
            print()
            print('🔍 書き込み後の確認:')
            read_client = ZohoClient()
            updated_record = read_client.get_app_hc_record(record_id)
            
            field_value = updated_record.get('transfer_activity_status')
            print(f'   transfer_activity_status フィールドの現在値: {field_value}')
            
            if field_value == test_data['transfer_activity_status']:
                print('   ✅ データが正常に更新されました')
            elif field_value:
                print(f'   ⚠️ 異なる値が設定されています: 期待値={test_data["transfer_activity_status"]}, 実際値={field_value}')
            else:
                print('   ❌ データが更新されていません')
                
            # さらに詳細な権限確認
            print()
            print('🔐 権限確認のための詳細調査:')
            print('   1. レコードロック状態の確認')
            print('   2. ユーザー権限の確認')
            print('   3. フィールドレベル権限の確認')
            
    except Exception as e:
        print(f'実行エラー: {str(e)}')
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()