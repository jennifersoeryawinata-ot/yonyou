"""rename_created_at_and_updated_at_to_date

Revision ID: 112953014996
Revises: 9991b5be540c
Create Date: 2026-09-21 11:59:46.274111

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

import sqlmodel
import utils 



# revision identifiers, used by Alembic.
revision: str = '112953014996'
down_revision: Union[str, None] = '9991b5be540c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename columns in table 'worker'
    op.alter_column('worker', 'created_at', new_column_name='created_date')
    op.alter_column('worker', 'updated_at', new_column_name='updated_date')

    # Rename columns in table 'role'
    op.alter_column('role', 'created_at', new_column_name='created_date')
    op.alter_column('role', 'updated_at', new_column_name='updated_date')


def downgrade() -> None:
    # Revert columns in table 'role'
    op.alter_column('role', 'updated_date', new_column_name='updated_at')
    op.alter_column('role', 'created_date', new_column_name='created_at')

    # Revert columns in table 'worker'
    op.alter_column('worker', 'updated_date', new_column_name='updated_at')
    op.alter_column('worker', 'created_date', new_column_name='created_at')


