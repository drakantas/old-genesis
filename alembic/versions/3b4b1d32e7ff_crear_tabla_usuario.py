"""Crear tabla usuario

Revision ID: 3b4b1d32e7ff
Revises: 54f282b63482
Create Date: 2017-09-01 14:35:03.415602

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b4b1d32e7ff'
down_revision = '54f282b63482'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('usuario',
                    sa.Column('id', sa.BigInteger, primary_key=True, index=True),
                    sa.Column('rol_id', sa.Integer, nullable=True),
                    sa.Column('correo_electronico', sa.String(128), unique=True, nullable=True, index=True),
                    sa.Column('credencial', sa.String(64), nullable=False),
                    sa.Column('nombres', sa.String(64), nullable=True, index=True),
                    sa.Column('apellidos', sa.String(64), nullable=True, index=True),
                    sa.Column('sexo', sa.SmallInteger, nullable=True),
                    sa.Column('tipo_documento', sa.SmallInteger, server_default=sa.DefaultClause('0'), nullable=False),
                    sa.Column('nacionalidad', sa.CHAR(2), nullable=True),
                    sa.Column('escuela', sa.SmallInteger, server_default=sa.DefaultClause('0'), nullable=True),
                    sa.Column('nro_telefono', sa.BigInteger, nullable=True),
                    sa.Column('distrito', sa.SmallInteger, nullable=True),
                    sa.Column('direccion', sa.String(64), nullable=True),
                    sa.Column('deshabilitado', sa.Boolean, server_default=sa.false(), nullable=False))


def downgrade():
    op.drop_table('usuario')
