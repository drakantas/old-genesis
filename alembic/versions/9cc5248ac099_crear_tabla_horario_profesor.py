"""Crear tabla horario profesor

Revision ID: 9cc5248ac099
Revises: cf6bd44b1c51
Create Date: 2017-09-17 23:06:36.043136

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9cc5248ac099'
down_revision = 'cf6bd44b1c51'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('horario_profesor',
                    sa.Column('ciclo_id', sa.SmallInteger, primary_key=True),
                    sa.Column('profesor_id', sa.BigInteger, primary_key=True),
                    sa.Column('dia_clase', sa.SmallInteger, default=0, primary_key=True),
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
