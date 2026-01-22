"""add_default_variable_mapping_to_templates

Revision ID: e7d8e399fd23
Revises: 0261f23a3702
Create Date: 2026-01-22 22:58:02.937161

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e7d8e399fd23'
down_revision: Union[str, Sequence[str], None] = '0261f23a3702'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('templates', sa.Column(
        'default_variable_mapping', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('templates', 'default_variable_mapping')
