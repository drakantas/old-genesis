"""Crear tabla solicitud_autorizacion

Revision ID: f0e2752cd775
Revises: 2d595d4fe6ea
Create Date: 2017-09-26 23:55:40.426331

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f0e2752cd775'
down_revision = '2d595d4fe6ea'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('solicitud_autorizacion',
                    sa.Column('alumno_id', sa.BigInteger, primary_key=True),
                    sa.Column('fecha_creacion', sa.DateTime, nullable=False),
                    sa.Column('archivo_id', sa.Integer, nullable=False))

    op.create_foreign_key('alumno_id_fk',
                          'solicitud_autorizacion', 'usuario',
                          ['alumno_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')

    op.create_foreign_key('archivo_id_fk',
                          'solicitud_autorizacion', 'archivo',
                          ['archivo_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_table('solicitud_autorizacion')
