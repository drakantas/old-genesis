"""Crear tabla grupo_notas

Revision ID: ef4615b22505
Revises: f0e2752cd775
Create Date: 2017-10-03 17:33:33.941939

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ef4615b22505'
down_revision = 'f0e2752cd775'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('grupo_notas',
                    sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
                    sa.Column('descripcion', sa.String(32), nullable=False))


def downgrade():
    op.drop_table('grupo_notas')
