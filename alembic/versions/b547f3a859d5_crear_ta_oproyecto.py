"""Crear ta oproyecto

Revision ID: b547f3a859d5
Revises: fa833048d77d
Create Date: 2017-09-01 15:07:44.110594

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b547f3a859d5'
down_revision = 'fa833048d77d'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('observacion_proyecto',
                    sa.Column('usuario_id', sa.BigInteger, primary_key=True),
                    sa.Column('proyecto_id', sa.Integer, primary_key=True),
                    sa.Column('contenido', sa.Text, nullable=False),

                    # Usaría jsonb pero en el supuesto de que cambiemos a mysql, mysql no soporta ese type
                    sa.Column('leido', sa.JSON, nullable=True))

    op.create_foreign_key('usuario_id_fk',
                          'observacion_proyecto', 'usuario',
                          ['usuario_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')

    op.create_foreign_key('proyecto_id_fk',
                          'observacion_proyecto', 'proyecto',
                          ['proyecto_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_table('observacion_proyecto')
