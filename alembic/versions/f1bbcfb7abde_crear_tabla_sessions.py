"""Crear tabla sessions

Revision ID: f1bbcfb7abde
Revises: 3d1fb6f10192
Create Date: 2017-09-10 19:11:44.680223

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1bbcfb7abde'
down_revision = '3d1fb6f10192'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('session',
                    sa.Column('id', sa.String(64), primary_key=True),
                    sa.Column('data', sa.JSON, nullable=True))


def downgrade():
    op.drop_table('session')
