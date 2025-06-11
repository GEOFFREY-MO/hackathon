"""remove price from sale

Revision ID: remove_price_from_sale
Revises: 
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'remove_price_from_sale'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Remove the price column from the sale table
    op.drop_column('sale', 'price')

def downgrade():
    # Add back the price column to the sale table
    op.add_column('sale', sa.Column('price', sa.Float(), nullable=False)) 