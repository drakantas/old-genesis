"""Crear tabla horario profesor

Revision ID: cf6bd44b1c51
Revises: 19ce90d214fd
Create Date: 2017-09-17 23:06:36.043136

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cf6bd44b1c51'
down_revision = '19ce90d214fd'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('horario_profesor',
                    sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
                    sa.Column('ciclo_id', sa.SmallInteger, nullable=False),
                    sa.Column('profesor_id', sa.BigInteger, nullable=False),
                    sa.Column('dia_clase', sa.SmallInteger, nullable=False),
                    sa.Column('hora_comienzo', sa.SmallInteger, default=0, nullable=False),
                    sa.Column('hora_fin', sa.SmallInteger, default=0, nullable=False))

    op.create_foreign_key('ciclo_id_fk',
                          'horario_profesor', 'ciclo_academico',
                          ['ciclo_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')

    op.create_foreign_key('profesor_id_fk',
                          'horario_profesor', 'usuario',
                          ['profesor_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_table('horario_profesor')
