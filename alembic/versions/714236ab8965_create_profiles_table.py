"""create profiles table

Revision ID: 714236ab8965
Revises: 1c655cc4913b
Create Date: 2024-01-16 10:54:20.269419

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import text, func


# revision identifiers, used by Alembic.
revision: str = '714236ab8965'
down_revision: Union[str, None] = '1c655cc4913b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Create profiles table
    op.create_table(
        'profiles',
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.user_id', ondelete='CASCADE'), primary_key=True),
        sa.Column('school', sa.String, nullable=True),
        sa.Column('rank', sa.Integer, nullable=True),
        sa.Column('affinities', JSONB, default=text('[]')),  # Use text to set a default value
        sa.Column('last_updated', sa.DateTime, nullable=True, default=func.timezone('UTC', func.now()), onupdate=func.timezone('UTC', func.now()))
    )

def downgrade():
    # Drop profiles table
    op.drop_table('profiles')
