from aiohttp.web import View
from aiohttp_jinja2 import template as view
from asyncpg.pool import PoolConnectionHolder

from utils.auth import get_auth_data
from utils.map import parse_data_key


class ApproveUsers(View):
    @view('admin/authorize_students.html')
    async def get(self):
        user = await get_auth_data(self.request)
        students = await self._fetch_students(user['escuela'], self.request.app.db)

        def _convert_data_keys(student):
            student['escuela'] = parse_data_key(student['escuela'], 'schools')
            student['tipo_documento'] = parse_data_key(student['tipo_documento'], 'id_types')
            return student

        students = list(map(_convert_data_keys, [dict(student) for student in students]))
        return {'students': students}

    @staticmethod
    async def _fetch_students(school: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT id, rol_id, tipo_documento, nombres, apellidos, correo_electronico, escuela, deshabilitado
            FROM usuario
            WHERE rol_id IS NULL AND
                  escuela=$1 AND
                  deshabilitado=true
            ORDER BY apellidos ASC
        '''
        async with dbi.acquire() as connection:
            stmt = await connection.prepare(query)
            return await stmt.fetch(school)


routes = {
    "admin/authorize-students": ApproveUsers
}
