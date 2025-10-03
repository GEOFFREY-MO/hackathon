"""add report table

Revision ID: add_report_table
Revises: 
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_report_table'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table('report',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('shop_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=100), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('parameters', sqlite.JSON),
        sa.Column('created_at', sa.DateTime(), default=sa.func.now()),
        sa.Column('last_generated', sa.DateTime()),
        sa.Column('schedule', sa.String(length=50)),
        sa.ForeignKeyConstraint(['shop_id'], ['shop.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('report') 