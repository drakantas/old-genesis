"""FK de rol en usuario

Revision ID: 3d1fb6f10192
Revises: b547f3a859d5
Create Date: 2017-09-01 15:16:14.536701

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d1fb6f10192'
down_revision = 'b547f3a859d5'
branch_labels = None
depends_on = None


def upgrade():
    op.create_foreign_key('rol_id_fk',
                          'usuario', 'rol_usuario',
                          ['rol_id'], ['id'],
                          ondelete='SET NULL', onupdate='CASCADE')


def downgrade():
    op.drop_constraint('rol_id_fk', 'usuario', type_='foreignkey')
