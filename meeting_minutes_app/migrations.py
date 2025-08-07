#!/usr/bin/env python3
"""
データベースマイグレーション管理スクリプト
Supabase, GCP Cloud SQL, その他のPostgreSQLプロバイダーに対応
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from alembic.config import Config
from alembic import command
from infrastructure.config.settings import settings


class DatabaseMigrationManager:
    """データベースマイグレーション管理クラス"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or settings.database_url
        self.alembic_cfg = self._setup_alembic_config()
    
    def _setup_alembic_config(self) -> Config:
        """Alembic設定をセットアップ"""
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
        return alembic_cfg
    
    def create_migration(self, message: str) -> None:
        """新しいマイグレーションを作成"""
        print(f"Creating migration: {message}")
        command.revision(self.alembic_cfg, message=message, autogenerate=True)
        print("✅ Migration created successfully!")
    
    def upgrade_database(self, revision: str = "head") -> None:
        """データベースをアップグレード"""
        print(f"Upgrading database to revision: {revision}")
        command.upgrade(self.alembic_cfg, revision)
        print("✅ Database upgrade completed!")
    
    def downgrade_database(self, revision: str) -> None:
        """データベースをダウングレード"""
        print(f"Downgrading database to revision: {revision}")
        command.downgrade(self.alembic_cfg, revision)
        print("✅ Database downgrade completed!")
    
    def show_current_revision(self) -> None:
        """現在のリビジョンを表示"""
        command.current(self.alembic_cfg, verbose=True)
    
    def show_migration_history(self) -> None:
        """マイグレーション履歴を表示"""
        command.history(self.alembic_cfg, verbose=True)
    
    def show_pending_migrations(self) -> None:
        """未適用のマイグレーションを表示"""
        print("Showing pending migrations...")
        command.show(self.alembic_cfg, "head")


def print_usage():
    """使用方法を表示"""
    print("""
データベースマイグレーション管理

使用方法:
  python migrations.py <command> [options]

コマンド:
  upgrade [revision]     - データベースをアップグレード（デフォルト: head）
  downgrade <revision>   - データベースをダウングレード
  create <message>       - 新しいマイグレーションを作成
  current                - 現在のリビジョンを表示
  history                - マイグレーション履歴を表示
  pending                - 未適用のマイグレーションを表示

例:
  python migrations.py upgrade              # 最新まで適用
  python migrations.py upgrade 001          # 特定リビジョンまで適用
  python migrations.py downgrade 001        # 特定リビジョンまでダウングレード
  python migrations.py create "add_user_table"  # 新しいマイグレーションを作成

環境変数:
  DATABASE_URL - データベース接続URL（.envファイルからも読み込み）
  
対応データベース:
  - Supabase (PostgreSQL)
  - GCP Cloud SQL (PostgreSQL)
  - 任意のPostgreSQLデータベース
""")


def main():
    """メイン関数"""
    
    if len(sys.argv) < 2:
        print_usage()
        return
    
    command_name = sys.argv[1].lower()
    
    # データベースURL表示
    print(f"Database URL: {settings.database_url}")
    print(f"Environment: {settings.environment}")
    print("-" * 50)
    
    try:
        manager = DatabaseMigrationManager()
        
        if command_name == "upgrade":
            revision = sys.argv[2] if len(sys.argv) > 2 else "head"
            manager.upgrade_database(revision)
        
        elif command_name == "downgrade":
            if len(sys.argv) < 3:
                print("❌ Error: downgrade requires a revision argument")
                print("Example: python migrations.py downgrade 001")
                return
            revision = sys.argv[2]
            manager.downgrade_database(revision)
        
        elif command_name == "create":
            if len(sys.argv) < 3:
                print("❌ Error: create requires a message argument")
                print("Example: python migrations.py create 'add user table'")
                return
            message = " ".join(sys.argv[2:])
            manager.create_migration(message)
        
        elif command_name == "current":
            manager.show_current_revision()
        
        elif command_name == "history":
            manager.show_migration_history()
        
        elif command_name == "pending":
            manager.show_pending_migrations()
        
        else:
            print(f"❌ Unknown command: {command_name}")
            print_usage()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()