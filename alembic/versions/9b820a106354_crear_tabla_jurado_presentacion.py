"""Crear tabla jurado presentacion

Revision ID: 9b820a106354
Revises: e357c52106a2
Create Date: 2017-10-15 15:17:41.094373

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9b820a106354'
down_revision = 'e357c52106a2'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('jurado_presentacion',
                    sa.Column('presentacion_id', sa.Integer, primary_key=True),
                    sa.Column('jurado_id', sa.BigInteger, primary_key=True))

    op.create_foreign_key('presentacion_id_fk',
                          'jurado_presentacion', 'presentacion_proyecto',
                          ['presentacion_id'], ['proyecto_id'],
                          ondelete='CASCADE', onupdate='CASCADE')

    op.create_foreign_key('jurado_id_fk',
                          'jurado_presentacion', 'usuario',
                          ['jurado_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_table('jurado_presentacion')
