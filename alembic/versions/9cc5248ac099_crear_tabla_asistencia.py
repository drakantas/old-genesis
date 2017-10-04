"""Crear tabla asistencia

Revision ID: 9cc5248ac099
Revises: cf6bd44b1c51
Create Date: 2017-09-11 17:36:06.940806

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9cc5248ac099'
down_revision = 'cf6bd44b1c51'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('asistencia',
                    sa.Column('alumno_id', sa.BigInteger, primary_key=True),
                    sa.Column('horario_id', sa.Integer, primary_key=True),
                    sa.Column('fecha_registro', sa.DateTime, primary_key=True),
                    sa.Column('observacion', sa.String(512), nullable=True),
                    sa.Column('asistio', sa.Boolean, nullable=False, default=True))

    op.create_foreign_key('alumno_id_fk',
                          'asistencia', 'usuario',
                          ['alumno_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')

    op.create_foreign_key('horario_id_fk',
                          'asistencia', 'horario_profesor',
                          ['horario_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_table('asistencia')
