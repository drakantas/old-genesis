"""Crear tabla proyecto

Revision ID: ff720c0275aa
Revises: 3b4b1d32e7ff
Create Date: 2017-09-01 14:53:35.141033

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ff720c0275aa'
down_revision = '3b4b1d32e7ff'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('proyecto',
                    sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
                    sa.Column('titulo', sa.String(128), nullable=False, unique=True, index=True),
                    sa.Column('ciclo_acad_id', sa.Integer, nullable=False))


def downgrade():
    op.drop_table('proyecto')
