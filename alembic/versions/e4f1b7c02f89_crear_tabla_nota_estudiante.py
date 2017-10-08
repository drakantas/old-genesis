"""Crear tabla nota_estudiante

Revision ID: e4f1b7c02f89
Revises: 9439aba13df1
Create Date: 2017-10-03 17:36:48.783114

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4f1b7c02f89'
down_revision = '9439aba13df1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('nota_estudiante',
                    sa.Column('nota_id', sa.Integer, primary_key=True),
                    sa.Column('estudiante_id', sa.Integer, primary_key=True),
                    sa.Column('valor', sa.Numeric(scale=4, precision=2), nullable=False))

    op.create_foreign_key('nota_id_fk',
                          'nota_estudiante', 'nota',
                          ['nota_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')

    op.create_foreign_key('estudiante_id_fk',
                          'nota_estudiante', 'usuario',
                          ['estudiante_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_table('nota_estudiante')
