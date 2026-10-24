"""initial_lab_schema

Revision ID: 0001_initial_lab_schema
Revises: 
Create Date: 2026-10-22 18:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '0001_initial_lab_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'lab_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('patient_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doctor_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('exam_type', sa.String(length=100), nullable=False),
        sa.Column('priority', sa.String(length=10), server_default='normal', nullable=False),
        sa.Column('clinical_notes', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=25), server_default='SOLICITADO', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("priority IN ('normal', 'urgente')", name='chk_lab_orders_priority'),
        sa.CheckConstraint("status IN ('SOLICITADO', 'EN_PROCESO', 'RESULTADO_CARGADO', 'ENTREGADO', 'CANCELADO')", name='chk_lab_orders_status'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_lab_orders_doctor_id', 'lab_orders', ['doctor_id'])
    op.create_index('idx_lab_orders_patient_id', 'lab_orders', ['patient_id'])
    op.create_index('idx_lab_orders_status', 'lab_orders', ['status'])

    op.create_table(
        'lab_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('stored_filename', sa.String(length=64), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('storage_path', sa.String(length=500), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint('file_size_bytes > 0', name='chk_lab_results_size'),
        sa.ForeignKeyConstraint(['order_id'], ['lab_orders.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('stored_filename')
    )
    op.create_index('idx_lab_results_order_id', 'lab_results', ['order_id'])
    op.create_index('idx_lab_results_sha256', 'lab_results', ['sha256_hash'])

def downgrade() -> None:
    op.drop_index('idx_lab_results_sha256', table_name='lab_results')
    op.drop_index('idx_lab_results_order_id', table_name='lab_results')
    op.drop_table('lab_results')
    op.drop_index('idx_lab_orders_status', table_name='lab_orders')
    op.drop_index('idx_lab_orders_patient_id', table_name='lab_orders')
    op.drop_index('idx_lab_orders_doctor_id', table_name='lab_orders')
    op.drop_table('lab_orders')