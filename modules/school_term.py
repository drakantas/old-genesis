from aiohttp.web import View
from datetime import datetime
from asyncpg.pool import PoolConnectionHolder

from utils.helpers import view
from utils.map import map_users


class CreateSchoolTerm(View):
    @view('school_term.create')
    async def get(self, user: dict):
        current_school_term, teachers = await self.get_school_term_and_teachers(user['escuela'])

        return {'teachers': teachers,
                'today': datetime.utcnow(),
                'current_school_term': current_school_term}

    @view('school_term.create')
    async def post(self, user: dict):
        current_school_term, teachers = await self.get_school_term_and_teachers(user['escuela'])

        data = await self.request.post()
        print(data)

        if not current_school_term:
            pass

        return {'teachers': teachers,
                'today': datetime.utcnow(),
                'current_school_term': current_school_term}

    async def get_school_term_and_teachers(self, school: int, role_id: int = 2, now: datetime = datetime.utcnow()):
        current_school_term = await self.fetch_current_school_term(now, self.request.app.db)
        teachers = map_users(await self.fetch_teachers(school, role_id, self.request.app.db))

        return current_school_term, teachers

    @staticmethod
    async def fetch_teachers(school: int, role_id: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT id, rol_id, tipo_documento, nombres, apellidos, correo_electronico, nro_telefono, escuela
            FROM usuario
            WHERE rol_id = $1 AND
                  deshabilitado != TRUE AND
                  escuela = $2
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetch(role_id, school)

    @staticmethod
    async def fetch_current_school_term(now: datetime, dbi: PoolConnectionHolder):
        query = '''
            SELECT id
            FROM ciclo_academico
            WHERE $1 >= fecha_comienzo AND
                  $1 <= fecha_fin
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(now)


class ViewSchoolTerm(View):
    @view('school_term.view')
    async def get(self):
        return {}


class UpdateSchoolTerm(View):
    @view('school_term.update')
    async def get(self):
        return {}


routes = {
    "school-term": {
        "create": CreateSchoolTerm,
        "view/{st_id:[1-9][0-9]*}": ViewSchoolTerm,
        "update/{st_id:[1-9][0-9]*}": UpdateSchoolTerm
    }
}