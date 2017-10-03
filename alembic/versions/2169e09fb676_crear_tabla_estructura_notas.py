"""Crear tabla estructura_notas

Revision ID: 2169e09fb676
Revises: e4f1b7c02f89
Create Date: 2017-10-03 17:39:37.873737

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2169e09fb676'
down_revision = 'e4f1b7c02f89'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('estructura_notas',
                    sa.Column('ciclo_acad_id', sa.Integer, primary_key=True),
                    sa.Column('nota_id', sa.Integer, primary_key=True))

    op.create_foreign_key('ciclo_acad_id_fk',
                          'estructura_notas', 'ciclo_academico',
                          ['ciclo_acad_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')

    op.create_foreign_key('nota_id_fk',
                          'estructura_notas', 'nota',
                          ['nota_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_table('estructura_notas')
