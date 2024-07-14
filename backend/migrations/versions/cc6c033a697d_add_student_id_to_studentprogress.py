"""Add student_id to StudentProgress

Revision ID: cc6c033a697d
Revises: d587d08120c6
Create Date: 2024-07-03 18:59:48.299183

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cc6c033a697d'
down_revision = 'd587d08120c6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('student_progress', schema=None) as batch_op:
        batch_op.add_column(sa.Column('student_id', sa.Integer(), nullable=False))
        batch_op.create_foreign_key('fk_student_progress_student', 'student', ['student_id'], ['id'])

def downgrade():
    with op.batch_alter_table('student_progress', schema=None) as batch_op:
        batch_op.drop_constraint('fk_student_progress_student', type_='foreignkey')
        batch_op.drop_column('student_id')