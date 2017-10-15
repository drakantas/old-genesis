"""Crear tabla presentacion proy

Revision ID: e357c52106a2
Revises: 9201dc23e775
Create Date: 2017-10-15 15:11:56.273254

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e357c52106a2'
down_revision = '9201dc23e775'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('presentacion_proyecto',
                    sa.Column('proyecto_id', sa.Integer, primary_key=True),
                    sa.Column('fecha', sa.DateTime))

    op.create_foreign_key('proyecto_id_fk',
                          'presentacion_proyecto', 'proyecto',
                          ['proyecto_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_table('presentacion_proyecto')
