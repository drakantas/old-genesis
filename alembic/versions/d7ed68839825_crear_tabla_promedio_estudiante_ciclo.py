"""Crear tabla promedio_estudiante_ciclo

Revision ID: d7ed68839825
Revises: 2169e09fb676
Create Date: 2017-10-03 17:56:16.149238

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7ed68839825'
down_revision = '2169e09fb676'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('promedio_notas_ciclo',
                    sa.Column('ciclo_acad_id', sa.Integer, primary_key=True),
                    sa.Column('estudiante_id', sa.Integer, primary_key=True),
                    sa.Column('valor', sa.Numeric(scale=2, precision=2), nullable=False))

    op.create_foreign_key('ciclo_acad_id_fk',
                          'promedio_notas_ciclo', 'ciclo_academico',
                          ['ciclo_acad_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')

    op.create_foreign_key('estudiante_id_fk',
                          'promedio_notas_ciclo', 'usuario',
                          ['estudiante_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_table('promedio_notas_ciclo')
