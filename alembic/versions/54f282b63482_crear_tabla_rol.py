"""Crear tabla rol

Revision ID: 54f282b63482
Revises: 
Create Date: 2017-09-01 14:28:55.921430

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '54f282b63482'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('rol_usuario',
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('desc', sa.String(16), unique=True, nullable=False))


def downgrade():
    op.drop_table('rol_usuario')
