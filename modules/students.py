from typing import Generator
from aiohttp.web import View
from asyncpg.pool import PoolConnectionHolder

from utils.map import map_users
from utils.helpers import view, permission_required


class AuthorizeStudents(View):
    @view('admin.authorize_students')
    @permission_required('autorizar_estudiantes')
    async def get(self, user: dict):
        students = await self._get_students(user, self.request.app.db)

        return {'students': students}

    @view('admin.authorize_students')
    @permission_required('autorizar_estudiantes')
    async def post(self, user: dict):
        students = await self._get_students(user, self.request.app.db)

        data = await self.request.post()
        data = list(self.checked_students(data, students))

        try:
            if data:
                await self.authorize_students(((s,) for s in data), self.request.app.db)
            else:
                raise ValueError
        except ValueError:
            alert = {'type': 'error'}
        else:
            alert = {'type': 'success'}

        return {'students': await self._get_students(user, self.request.app.db),
                'alert': alert}

    async def _get_students(self, user: dict, dbi: PoolConnectionHolder) -> list:
        students = await self._fetch_students(user['escuela'], dbi)
        return map_users(students)

    @staticmethod
    def checked_students(data: dict, students: list) -> Generator:
        for student in students:
            if 'student_{}'.format(student['id']) in data:
                yield student['id']

    @staticmethod
    async def authorize_students(data: Generator, dbi: PoolConnectionHolder):
        query = '''
            UPDATE usuario
            SET autorizado=TRUE
            WHERE id=$1
        '''

        async with dbi.acquire() as connection:
            async with connection.transaction():
                await connection.executemany(query, data)

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
            WHERE rol_id=1 AND
                  escuela=$1 AND
                  autorizado=FALSE AND
                  deshabilitado=FALSE
            ORDER BY apellidos ASC
        '''
        async with dbi.acquire() as connection:
            stmt = await connection.prepare(query)
            return await stmt.fetch(school)


routes = {
    "students/authorize": AuthorizeStudents
}
