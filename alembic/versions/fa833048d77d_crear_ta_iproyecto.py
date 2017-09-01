"""Crear tabla asociativa IntegranteProyecto

Revision ID: fa833048d77d
Revises: ff720c0275aa
Create Date: 2017-09-01 14:56:43.355568

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fa833048d77d'
down_revision = 'ff720c0275aa'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('integrante_proyecto',
                    sa.Column('usuario_id', sa.BigInteger, primary_key=True),
                    sa.Column('proyecto_id', sa.Integer, primary_key=True),
                    sa.Column('fecha_integrar', sa.DateTime(timezone=True), nullable=False))

    op.create_foreign_key('usuario_id_fk',
                          'integrante_proyecto', 'usuario',
                          ['usuario_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')

    op.create_foreign_key('proyecto_id_fk',
                          'integrante_proyecto', 'proyecto',
                          ['proyecto_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_table('integrante_proyecto')
