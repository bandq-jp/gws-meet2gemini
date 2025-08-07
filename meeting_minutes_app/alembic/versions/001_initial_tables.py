"""Initial tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create meeting_documents table
    op.create_table('meeting_documents',
        sa.Column('id', sa.String(), nullable=False, comment='議事録ドキュメントの一意ID'),
        sa.Column('document_id', sa.String(length=100), nullable=False, comment='GoogleドキュメントID'),
        sa.Column('account_email', sa.String(length=255), nullable=False, comment='アカウントメールアドレス'),
        sa.Column('metadata', sa.JSON(), nullable=False, comment='会議メタデータ（タイトル、日時、参加者等）'),
        sa.Column('text_content', sa.Text(), nullable=False, comment='議事録のテキスト内容'),
        sa.Column('doc_structure', sa.JSON(), nullable=True, comment='Google Docs APIから取得した文書構造'),
        sa.Column('downloaded_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='ドキュメント取得日時'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='レコード作成日時'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='レコード更新日時'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for meeting_documents
    op.create_index('idx_meeting_account_email', 'meeting_documents', ['account_email'])
    op.create_index('idx_meeting_created_at', 'meeting_documents', ['created_at'])
    op.create_index('idx_meeting_updated_at', 'meeting_documents', ['updated_at'])
    op.create_index('idx_meeting_doc_duplicate', 'meeting_documents', ['document_id', 'account_email'], unique=True)
    
    # Create structured_data table
    op.create_table('structured_data',
        sa.Column('id', sa.String(), nullable=False, comment='構造化データの一意ID'),
        sa.Column('meeting_document_id', sa.String(), nullable=False, comment='関連する議事録ドキュメントID'),
        
        # 転職活動状況・エージェント関連
        sa.Column('transfer_activity_status', sa.String(length=100), nullable=True, comment='転職活動状況'),
        sa.Column('agent_count', sa.String(length=50), nullable=True, comment='エージェント数'),
        sa.Column('current_agents', sa.Text(), nullable=True, comment='現在利用中のエージェント'),
        sa.Column('introduced_jobs', sa.Text(), nullable=True, comment='紹介された求人'),
        sa.Column('job_appeal_points', sa.Text(), nullable=True, comment='求人の魅力点'),
        sa.Column('job_concerns', sa.Text(), nullable=True, comment='求人の懸念点'),
        sa.Column('companies_in_selection', sa.JSON(), nullable=True, comment='選考中の企業（配列）'),
        sa.Column('other_offer_salary', sa.String(length=100), nullable=True, comment='他社オファー年収'),
        sa.Column('other_company_intention', sa.JSON(), nullable=True, comment='他社意向度（配列）'),
        
        # 転職理由・希望条件
        sa.Column('transfer_reasons', sa.JSON(), nullable=True, comment='転職理由（配列）'),
        sa.Column('transfer_trigger', sa.JSON(), nullable=True, comment='転職きっかけ（配列）'),
        sa.Column('desired_timing', sa.String(length=50), nullable=True, comment='希望転職時期'),
        sa.Column('timing_details', sa.Text(), nullable=True, comment='転職時期詳細'),
        sa.Column('current_job_status', sa.String(length=50), nullable=True, comment='現職状況'),
        sa.Column('transfer_status_memo', sa.JSON(), nullable=True, comment='転職状況メモ（配列）'),
        sa.Column('transfer_priorities', sa.JSON(), nullable=True, comment='転職軸（配列）'),
        
        # 職歴・経験
        sa.Column('career_history', sa.JSON(), nullable=True, comment='職歴（配列）'),
        sa.Column('current_duties', sa.Text(), nullable=True, comment='現在の担当業務'),
        sa.Column('company_good_points', sa.Text(), nullable=True, comment='現職企業の良い点'),
        sa.Column('company_bad_points', sa.Text(), nullable=True, comment='現職企業の悪い点'),
        sa.Column('enjoyed_work', sa.Text(), nullable=True, comment='楽しかった仕事'),
        sa.Column('difficult_work', sa.Text(), nullable=True, comment='辛かった仕事'),
        
        # 希望業界・職種
        sa.Column('experience_industry', sa.String(length=100), nullable=True, comment='経験業界'),
        sa.Column('experience_field_hr', sa.String(length=100), nullable=True, comment='人材領域での経験'),
        sa.Column('desired_industry', sa.JSON(), nullable=True, comment='希望業界（配列）'),
        sa.Column('industry_reason', sa.JSON(), nullable=True, comment='業界希望理由（配列）'),
        sa.Column('desired_position', sa.JSON(), nullable=True, comment='希望職種（配列）'),
        sa.Column('position_industry_reason', sa.JSON(), nullable=True, comment='職種・業界希望理由（配列）'),
        
        # 年収・待遇条件
        sa.Column('current_salary', sa.Integer(), nullable=True, comment='現在の年収'),
        sa.Column('salary_breakdown', sa.Text(), nullable=True, comment='年収内訳'),
        sa.Column('desired_first_year_salary', sa.Float(), nullable=True, comment='初年度希望年収'),
        sa.Column('base_incentive_ratio', sa.String(length=100), nullable=True, comment='基本給・インセンティブ比率'),
        sa.Column('max_future_salary', sa.String(length=100), nullable=True, comment='将来最大年収'),
        sa.Column('salary_memo', sa.JSON(), nullable=True, comment='給与メモ（配列）'),
        sa.Column('remote_time_memo', sa.JSON(), nullable=True, comment='リモート・時間メモ（配列）'),
        sa.Column('ca_ra_focus', sa.String(length=100), nullable=True, comment='CA起点/RA起点'),
        sa.Column('customer_acquisition', sa.String(length=200), nullable=True, comment='集客方法'),
        sa.Column('new_existing_ratio', sa.String(length=100), nullable=True, comment='新規・既存比率'),
        
        # 企業文化・キャリアビジョン
        sa.Column('business_vision', sa.JSON(), nullable=True, comment='事業構想（配列）'),
        sa.Column('desired_employee_count', sa.JSON(), nullable=True, comment='希望従業員数（配列）'),
        sa.Column('culture_scale_memo', sa.JSON(), nullable=True, comment='企業文化・規模メモ（配列）'),
        sa.Column('career_vision', sa.JSON(), nullable=True, comment='キャリアビジョン（配列）'),
        
        # 抽出メタデータ
        sa.Column('extraction_metadata', sa.JSON(), nullable=True, comment='抽出処理のメタデータ'),
        sa.Column('extraction_status', sa.String(length=50), nullable=False, server_default='pending', comment='抽出ステータス（pending/completed/failed）'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='レコード作成日時'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()'), comment='レコード更新日時'),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['meeting_document_id'], ['meeting_documents.id'], ondelete='CASCADE')
    )
    
    # Create indexes for structured_data
    op.create_index('idx_structured_meeting_doc_id', 'structured_data', ['meeting_document_id'])
    op.create_index('idx_structured_extraction_status', 'structured_data', ['extraction_status'])
    op.create_index('idx_structured_created_at', 'structured_data', ['created_at'])
    op.create_index('idx_structured_updated_at', 'structured_data', ['updated_at'])
    op.create_index('idx_structured_activity_status', 'structured_data', ['transfer_activity_status'])
    op.create_index('idx_structured_current_salary', 'structured_data', ['current_salary'])


def downgrade() -> None:
    # Drop structured_data table and its indexes
    op.drop_index('idx_structured_current_salary', table_name='structured_data')
    op.drop_index('idx_structured_activity_status', table_name='structured_data')
    op.drop_index('idx_structured_updated_at', table_name='structured_data')
    op.drop_index('idx_structured_created_at', table_name='structured_data')
    op.drop_index('idx_structured_extraction_status', table_name='structured_data')
    op.drop_index('idx_structured_meeting_doc_id', table_name='structured_data')
    op.drop_table('structured_data')
    
    # Drop meeting_documents table and its indexes
    op.drop_index('idx_meeting_doc_duplicate', table_name='meeting_documents')
    op.drop_index('idx_meeting_updated_at', table_name='meeting_documents')
    op.drop_index('idx_meeting_created_at', table_name='meeting_documents')
    op.drop_index('idx_meeting_account_email', table_name='meeting_documents')
    op.drop_table('meeting_documents')