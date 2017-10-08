"""Crear tabla matricula

Revision ID: feedf0038e90
Revises: d7ed68839825
Create Date: 2017-10-08 17:13:12.839473

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'feedf0038e90'
down_revision = 'd7ed68839825'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('matricula',
                    sa.Column('estudiante_id', sa.BigInteger, primary_key=True),
                    sa.Column('ciclo_acad_id', sa.Integer, primary_key=True))

    op.create_foreign_key('estudiante_id_fk',
                          'matricula', 'usuario',
                          ['estudiante_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')

    op.create_foreign_key('ciclo_acad_id_fk',
                          'matricula', 'ciclo_academico',
                          ['ciclo_acad_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_table('matricula')
