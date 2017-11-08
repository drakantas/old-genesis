"""Crear tabla de títulos académicos.

Revision ID: eb3f4cf15d9f
Revises: 9b820a106354
Create Date: 2017-11-08 11:23:29.882093

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'eb3f4cf15d9f'
down_revision = '9b820a106354'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('titulo_usuario',
                    sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
                    sa.Column('descripcion', sa.String(16), nullable=False, unique=True))

    op.add_column('usuario', sa.Column('titulo_id', sa.Integer, nullable=True))

    op.create_foreign_key('titulo_usuario_id_fk',
                          'usuario', 'titulo_usuario',
                          ['titulo_id'], ['id'],
                          ondelete='CASCADE', onupdate='CASCADE')


def downgrade():
    op.drop_constraint('titulo_usuario_id_fk', 'usuario', type_='foreignkey')

    op.drop_table('titulo_usuario')

    op.drop_column('usuario', 'titulo_id')
