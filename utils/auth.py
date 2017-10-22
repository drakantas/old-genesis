from datetime import datetime
from aiohttp_session import get_session
from aiohttp.web import Request, HTTPFound


class NotAuthenticated(Exception):
    pass


async def get_auth_data(request: Request) -> dict:
    session = await get_session(request)

    if 'id' not in session:
        raise NotAuthenticated

    async with request.app.db.acquire() as connection:
        query = '''
            SELECT usuario.id, rol_usuario.desc as rol, correo_electronico,
                   nombres, apellidos, sexo,
                   tipo_documento, nacionalidad, escuela,
                   nro_telefono, distrito, direccion,
                   deshabilitado, avatar, autorizado,
                   rol_usuario.ver_listado_alumnos as perm_ver_listado_alumnos,
                   rol_usuario.ver_reportes_personales as perm_ver_reportes_personales,
                   rol_usuario.ver_notas_de_clase as perm_ver_notas_de_clase,
                   rol_usuario.ver_listado_proyectos as perm_ver_listado_proyectos,
                   rol_usuario.asignar_notas as perm_asignar_notas,
                   rol_usuario.registrar_asistencia as perm_registrar_asistencia,
                   rol_usuario.crear_proyecto as perm_crear_proyecto,
                   rol_usuario.gestionar_asistencias as perm_gestionar_asistencias,
                   rol_usuario.gestionar_notas as perm_gestionar_notas,
                   rol_usuario.gestionar_proyectos as perm_gestionar_proyectos,
                   rol_usuario.revisar_proyectos as perm_revisar_proyectos,
                   rol_usuario.autorizar_estudiantes as perm_autorizar_estudiantes,
                   rol_usuario.mantener_usuarios as perm_mantener_usuarios,
                   rol_usuario.mantener_roles as perm_mantener_roles,
                   (SELECT true
                    FROM proyecto
                    RIGHT JOIN integrante_proyecto
                            ON integrante_proyecto.proyecto_id = proyecto.id AND
                               integrante_proyecto.usuario_id = usuario.id AND
                               integrante_proyecto.aceptado = true
                    WHERE proyecto.ciclo_acad_id = (SELECT id FROM ciclo_academico
                                                    WHERE ciclo_academico.fecha_comienzo <= $2 AND
                                                          ciclo_academico.fecha_fin >= $2 AND
                                                          ciclo_academico.escuela = usuario.escuela
                                                    LIMIT 1) AND
                          integrante_proyecto.usuario_id = usuario.id
                   ) as has_project,
                   (SELECT COUNT(true)
                    FROM integrante_proyecto
                    LEFT JOIN proyecto
                           ON proyecto.id = integrante_proyecto.proyecto_id
                    WHERE integrante_proyecto.usuario_id = usuario.id AND
                          integrante_proyecto.aceptado = FALSE AND
                          proyecto.ciclo_acad_id = (SELECT id FROM ciclo_academico
                                                    WHERE ciclo_academico.fecha_comienzo <= $2 AND
                                                          ciclo_academico.fecha_fin >= $2 AND
                                                          ciclo_academico.escuela = usuario.escuela
                                                    LIMIT 1)
                    LIMIT 1
                   ) as invitaciones,
                   (SELECT COUNT(true)
                    FROM observacion_proyecto
                    LEFT JOIN proyecto
                           ON proyecto.id = observacion_proyecto.proyecto_id
                    WHERE proyecto.ciclo_acad_id = (SELECT id FROM ciclo_academico
                                                    WHERE ciclo_academico.fecha_comienzo <= $2 AND
                                                          ciclo_academico.fecha_fin >= $2 AND
                                                          ciclo_academico.escuela = usuario.escuela
                                                    LIMIT 1) AND
                          finalizado = FALSE AND
                          observacion_proyecto.usuario_id = usuario.id
                   ) as observaciones_pendientes
            FROM usuario
            LEFT JOIN rol_usuario
                   ON rol_usuario.id = usuario.rol_id
            WHERE usuario.id = $1
        '''
        stmt = await connection.prepare(query)
        user = await stmt.fetchrow(int(session['id']), datetime.utcnow())

        if not user['autorizado'] or user['deshabilitado']:
            del session['id']
            raise HTTPFound('/')

        return user
