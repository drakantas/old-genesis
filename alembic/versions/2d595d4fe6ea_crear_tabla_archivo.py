"""Crear tabla archivo

Revision ID: 2d595d4fe6ea
Revises: 9cc5248ac099
Create Date: 2017-09-26 23:39:53.746158

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2d595d4fe6ea'
down_revision = '9cc5248ac099'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('archivo',
                    sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
                    sa.Column('nombre', sa.String(128), nullable=False),
                    sa.Column('ext', sa.String(12), nullable=False),
                    sa.Column('contenido', sa.Binary, nullable=False),
                    sa.Column('fecha_subido', sa.DateTime, nullable=False))


def downgrade():
    op.drop_table('archivo')
