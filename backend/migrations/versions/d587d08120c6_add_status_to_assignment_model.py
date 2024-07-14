"""Add status to Assignment model

Revision ID: d587d08120c6
Revises: eaef9448a6f1
Create Date: 2024-07-03 15:31:42.970709

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd587d08120c6'
down_revision = 'eaef9448a6f1'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('assignment', schema=None) as batch_op:
        batch_op.add_column(sa.Column('status', sa.String(length=20), nullable=False, server_default='Not Started'))

def downgrade():
    with op.batch_alter_table('assignment', schema=None) as batch_op:
        batch_op.drop_column('status')

    # ### end Alembic commands ###
