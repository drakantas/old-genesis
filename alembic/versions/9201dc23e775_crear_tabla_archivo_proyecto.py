"""Crear tabla archivo proyecto

Revision ID: 9201dc23e775
Revises: feedf0038e90
Create Date: 2017-10-15 15:00:25.835529

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9201dc23e775'
down_revision = 'feedf0038e90'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('archivo_proyecto',
                    sa.Column('archivo_id', sa.Integer, primary_key=True),
                    sa.Column('proyecto_id', sa.Integer, primary_key=True),
                    sa.Column('subido_por', sa.BigInteger, nullable=False))

    op.create_foreign_key('archivo_id_fk',
                          'archivo_proyecto', 'archivo',
                          ['archivo_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')

    op.create_foreign_key('proyecto_id_fk',
                          'archivo_proyecto', 'proyecto',
                          ['proyecto_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')

    op.create_foreign_key('subido_por_fk',
                          'archivo_proyecto', 'usuario',
                          ['subido_por'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_table('archivo_proyecto')
