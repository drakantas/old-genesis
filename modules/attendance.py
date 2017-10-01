from aiohttp.web import View
from datetime import datetime
from asyncpg.pool import PoolConnectionHolder

from utils.map import map_users
from utils.helpers import view as view


class StudentsList(View):
    @view('teacher.list')
    async def get(self, user: dict):
        display_amount = 10

        if 'display_amount' in self.request.match_info:
            display_amount = self.request.match_info['display_amount']
            if display_amount == 'all':
                display_amount = 1000
            else:
                display_amount = int(display_amount)

        students = await self.get_students(user['escuela'], display_amount, self.request.app.db)
        students = map_users(students)

        return {'students': students}

    @staticmethod
    async def get_students(school: int, amount: int, dbi: PoolConnectionHolder, student_role_id: int = 1,
                           danger: int = 63):
        query = '''
            WITH ciclo_academico AS (
                SELECT fecha_comienzo, fecha_fin
                FROM ciclo_academico
                WHERE $1 >= fecha_comienzo AND
                      $1 <= fecha_fin
                LIMIT 1
            ),
            alumno AS (
                SELECT id, tipo_documento, nombres, apellidos, escuela,
                    COALESCE(
                        (SELECT CAST(COUNT(CASE WHEN asistio=true THEN 1 ELSE NULL END) / CAST(COUNT(*) AS FLOAT) * 100
                        AS INT)
                            FROM asistencia
                            RIGHT JOIN ciclo_academico
                                    ON ciclo_academico.fecha_comienzo <= asistencia.fecha AND
                                       ciclo_academico.fecha_fin >= asistencia.fecha
                       WHERE asistencia.alumno_id = usuario.id
                       HAVING COUNT(*) >= 1),
                    0) AS asistencia,
                    COALESCE(
                        (SELECT proyecto_id 
                         FROM integrante_proyecto
                         WHERE integrante_proyecto.usuario_id = usuario.id
                         LIMIT 1),
                    NULL) AS id_proyecto
                FROM usuario
                WHERE rol_id = $2 AND
                      escuela = $3 AND
                      nombres != '' AND
                      apellidos != ''
                LIMIT $4
            )
            SELECT id, tipo_documento, nombres, apellidos, asistencia, escuela,
                   CASE WHEN asistencia < $5 THEN true ELSE false END as peligro,
                   id_proyecto
            FROM alumno
            ORDER BY apellidos ASC
        '''

        async with dbi.acquire() as connection:
            stmt = await connection.prepare(query)
            return await stmt.fetch(datetime.utcnow(), student_role_id, school, amount, danger)


class RegisterAttendance(View):
    @view('teacher.register')
    async def get(self, user: dict):
        semester, students = await self.get_semester_and_students(user['escuela'])

        return {'semester': semester,
                'students': students}

    @view('teacher.register_attendance')
    async def post(self, user: dict):
        semester, students = await self.get_semester_and_students(user['escuela'])

        if not semester:
            raise ValueError

        data = dict(await self.request.post())
        data = await self.convert_data(data, students)
        data = await self.format_data(data, user)

        result = await self.register_attendance(data, self.request.app.db)

        if isinstance(result, list):
            result = True

        return {'semester': semester,
                'students': students,
                'result': result}

    async def get_semester_and_students(self, school: int):
        semester = await self.fetch_semester(self.request.app.db)
        students = await self.fetch_students(school, self.request.app.db)

        return semester, students

    @staticmethod
    async def convert_data(data: dict, students: list) -> list:
        new_data = list()

        for s in students:
            data_keys = data.keys()
            attended = 'student_{}'.format(s['id'])
            additional = 'additional_{}'.format(s['id'])

            if additional not in data_keys:
                raise ValueError

            if attended not in data_keys:
                attended_bool = False
            elif data[attended] == 'on':
                attended_bool = True
            else:
                raise ValueError

            new_data.append([s['id'], data[additional], attended_bool])

        return new_data

    @staticmethod
    async def format_data(data: list, user: dict) -> list:
        current_time = datetime.utcnow()
        return [[s[0], user['id'], current_time, s[1], s[2]] for s in data]

    @staticmethod
    async def register_attendance(data: list, dbi: PoolConnectionHolder):
        async with dbi.acquire() as connection:
            async with connection.transaction():
                query = '''
                    INSERT INTO asistencia (alumno_id, profesor_id, fecha, observacion, asistio)
                    VALUES {0}
                    RETURNING true;
                '''.format(','.join(['({})'.format(
                    ','.join(list(
                        map(lambda x: '\''+str(x)+'\'' if not isinstance(x, str) else '\''+x+'\'', v)
                    ))) for v in data]))

                return await connection.fetch(query)

    @staticmethod
    async def fetch_students(school: int,  dbi: PoolConnectionHolder, role: int = 1):
        query = '''
            SELECT id, nombres, apellidos
            FROM usuario
            WHERE rol_id = $1 AND
                  escuela = $2
            ORDER BY apellidos ASC
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetch(role, school)

    @staticmethod
    async def fetch_semester(dbi: PoolConnectionHolder):
        query = '''
            SELECT fecha_comienzo, fecha_fin
            FROM ciclo_academico
            WHERE $1 >= fecha_comienzo AND
                  $1 <= fecha_fin
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetch(datetime.utcnow())


routes = {
    "students": {
        "list": StudentsList,
        "list/{display_amount:(?:10|25|all)}": StudentsList
    },
    "attendance": {
        "register": RegisterAttendance
    }
}
