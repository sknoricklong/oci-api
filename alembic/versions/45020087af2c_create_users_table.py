from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision = '45020087af2c'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'users',
        sa.Column('user_id', UUID(as_uuid=True), primary_key=True, server_default=text("(gen_random_uuid())")),
        sa.Column('email', sa.String, unique=True, nullable=False),
        sa.Column('password', sa.String, nullable=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.text("(timezone('utc', CURRENT_TIMESTAMP))")),
    )

def downgrade():
    op.drop_table('users')