"""create applications table

Revision ID: 160f6308ccbb
Revises: 1c655cc4913b
Create Date: 2024-01-16 10:34:43.907627

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = '160f6308ccbb'
down_revision: Union[str, None] = '45020087af2c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.create_table(
        'applications',
        sa.Column('application_id', sa.Integer, primary_key=True, index=True, autoincrement=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.user_id', ondelete='CASCADE'), nullable=False),
        sa.Column('firm', sa.String, nullable=True),
        sa.Column('city', sa.String, nullable=True),
        sa.Column('networked', sa.String, nullable=True),
        sa.Column('applied_date', sa.Date, nullable=True),
        sa.Column('applied_response_date', sa.Date, nullable=True),
        sa.Column('applied_to_response', sa.Integer, nullable=True),
        sa.Column('screener_date', sa.Date, nullable=True),
        sa.Column('screener_response_date', sa.Date, nullable=True),
        sa.Column('screener_to_response', sa.Integer, nullable=True),
        sa.Column('callback_date', sa.Date, nullable=True),
        sa.Column('callback_response_date', sa.Date, nullable=True),
        sa.Column('callback_to_response', sa.Integer, nullable=True),
        sa.Column('outcome', sa.Boolean, nullable=True),
        sa.Column('last_updated', sa.DateTime, nullable=True, default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint('user_id', 'firm', 'city', name='_user_firm_city_uc')
    )

def downgrade():
    op.drop_table('applications')
