"""Crear tabla rol

Revision ID: 54f282b63482
Revises: 
Create Date: 2017-09-01 14:28:55.921430

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '54f282b63482'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('rol_usuario',
                    sa.Column('id', sa.Integer, primary_key=True),
                    sa.Column('desc', sa.String(32), unique=True, nullable=False),
                    sa.Column('ver_listado_alumnos', sa.Boolean, nullable=False, server_default=sa.false()),
                    sa.Column('ver_reportes_personales', sa.Boolean, nullable=False, server_default=sa.false()),
                    sa.Column('ver_notas_de_clase', sa.Boolean, nullable=False, server_default=sa.false()),
                    sa.Column('ver_listado_proyectos', sa.Boolean, nullable=False, server_default=sa.false()),
                    sa.Column('asignar_notas', sa.Boolean, nullable=False, server_default=sa.false()),
                    sa.Column('registrar_asistencia', sa.Boolean, nullable=False, server_default=sa.false()),
                    sa.Column('crear_proyecto', sa.Boolean, nullable=False, server_default=sa.false()),
                    sa.Column('gestionar_proyectos', sa.Boolean, nullable=False, server_default=sa.false()),
                    sa.Column('revisar_proyectos', sa.Boolean, nullable=False, server_default=sa.false()),
                    sa.Column('autorizar_estudiantes', sa.Boolean, nullable=False, server_default=sa.false()),
                    sa.Column('mantener_usuarios', sa.Boolean, nullable=False, server_default=sa.false()),
                    sa.Column('mantener_roles', sa.Boolean, nullable=False, server_default=sa.false()))


def downgrade():
    op.drop_table('rol_usuario')
