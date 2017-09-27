from aiohttp.web import View
from aiohttp_jinja2 import template as view
from asyncpg.pool import PoolConnectionHolder

from utils.auth import get_auth_data
from utils.map import parse_data_key, map_users


class ApproveUsers(View):
    @view('admin/authorize_students.html')
    async def get(self):
        user = await get_auth_data(self.request)
        students = await self._fetch_students(user['escuela'], self.request.app.db)
        students = map_users(students)

        return {'students': students}

    @staticmethod
    async def _fetch_students(school: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT usuario.id, rol_id, tipo_documento, nombres, apellidos, correo_electronico, escuela, deshabilitado,
                   solicitud_autorizacion.fecha_creacion, archivo_id, archivo.nombre as archivo_nombre,
                   archivo.ext as archivo_ext
            FROM usuario
            INNER JOIN solicitud_autorizacion
                    ON usuario.id = solicitud_autorizacion.alumno_id
            INNER JOIN archivo
                    ON archivo.id = solicitud_autorizacion.archivo_id
            WHERE rol_id IS NULL AND
                  escuela=$1 AND
                  autorizado=FALSE AND
                  deshabilitado=FALSE
            ORDER BY apellidos ASC
        '''
        async with dbi.acquire() as connection:
            stmt = await connection.prepare(query)
            return await stmt.fetch(school)


routes = {
    "admin/authorize-students": ApproveUsers
}
