"""add notes column to applications table

Revision ID: 1c655cc4913b
Revises: 45020087af2c
Create Date: 2024-01-16 10:32:32.944841

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c655cc4913b'
down_revision: Union[str, None] = '160f6308ccbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.add_column('applications', sa.Column('notes', sa.Text, nullable=True))

def downgrade():
    op.drop_column('applications', 'notes')
