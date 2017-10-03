"""Crear tabla nota

Revision ID: 9439aba13df1
Revises: ef4615b22505
Create Date: 2017-10-03 17:34:58.491595

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9439aba13df1'
down_revision = 'ef4615b22505'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('nota',
                    sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
                    sa.Column('grupo_id', sa.Integer, nullable=True),
                    sa.Column('descripcion', sa.String(32), nullable=False),
                    sa.Column('porcentaje', sa.SmallInteger, nullable=False))


def downgrade():
    op.drop_table('nota')
