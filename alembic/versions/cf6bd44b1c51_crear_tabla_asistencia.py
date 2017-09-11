"""Crear tabla asistencia

Revision ID: cf6bd44b1c51
Revises: 19ce90d214fd
Create Date: 2017-09-11 17:36:06.940806

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cf6bd44b1c51'
down_revision = '19ce90d214fd'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('asistencia',
                    sa.Column('alumno_id', sa.BigInteger, primary_key=True),
                    sa.Column('profesor_id', sa.BigInteger, primary_key=True),
                    sa.Column('fecha', sa.DateTime, primary_key=True),
                    sa.Column('observacion', sa.String(512), nullable=True))

    op.create_foreign_key('alumno_id_fk',
                          'asistencia', 'usuario',
                          ['alumno_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')

    op.create_foreign_key('profesor_id_fk',
                          'asistencia', 'usuario',
                          ['profesor_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_table('asistencia')
