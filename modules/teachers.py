from datetime import datetime
from aiohttp.web import View
from aiohttp_jinja2 import template as view

from utils.auth import get_auth_data, NotAuthenticated


class StudentsList(View):
    @view('teacher/students_list.html')
    async def get(self):
        display_amount = 10

        if 'display_amount' in self.request.match_info:
            display_amount = self.request.match_info['display_amount']
            if display_amount == 'all':
                display_amount = 1000
            else:
                display_amount = int(display_amount)

        user = await get_auth_data(self.request)
        students = await self.get_students(user['escuela'], display_amount)

        return {'students': students}

    async def get_students(self, school: int, amount: int, student_role_id: int = 1, danger: int = 80):
        query = '''
            WITH ciclo_academico AS (
                SELECT fecha_comienzo, fecha_fin
                FROM ciclo_academico
                WHERE $1 >= fecha_comienzo AND
                      $1 <= fecha_fin
                LIMIT 1
            ),
            alumno AS (
                SELECT id, nombres, apellidos, 
                    COALESCE(
                        (SELECT CAST(COUNT(CASE WHEN asistio=true THEN 1 ELSE NULL END) / CAST(COUNT(*) AS FLOAT) * 100 AS INT)
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
            SELECT id, nombres, apellidos, asistencia,
                   CASE WHEN asistencia < $5 THEN true ELSE false END as peligro,
                   id_proyecto
            FROM alumno
            ORDER BY apellidos ASC
        '''

        async with self.request.app.db.acquire() as connection:
            stmt = await connection.prepare(query)
            return await stmt.fetch(datetime.utcnow(), student_role_id, school, amount, danger)


class RegisterAttendance(View):
    @view('teacher/register_attendance.html')
    async def get(self):
        user = await get_auth_data(self.request)
        semester, students = await self.fetch_semester(), await self.fetch_students(user['escuela'])

        return {'semester': semester,
                'students': students}

    @view('teacher/register_attendance.html')
    async def post(self):
        user = await get_auth_data(self.request)
        semester, students = await self.fetch_semester(), await self.fetch_students(user['escuela'])

        if not semester:
            raise ValueError

        data = dict(await self.request.post())
        data = await self.convert_data(data, students)
        data = await self.format_data(data, user)

        result = await self.register_attendance(data)

        if isinstance(result, list):
            result = True

        return {'semester': semester,
                'students': students,
                'result': result}

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

    async def register_attendance(self, data: list):
        async with self.request.app.db.acquire() as connection:
            async with connection.transaction():
                query = '''
                    INSERT INTO asistencia (alumno_id, profesor_id, fecha, observacion, asistio)
                    VALUES {0}
                    RETURNING true;
                '''.format(','.join(['({})'.format(','.join(list(map(lambda x: '\''+str(x)+'\'' if not isinstance(x, str) else '\''+x+'\'', v)))) for v in data]))

                return await connection.fetch(query)

    async def fetch_students(self, school: int, role: int = 1):
        query = '''
            SELECT id, nombres, apellidos
            FROM usuario
            WHERE rol_id = $1 AND
                  escuela = $2
            ORDER BY apellidos ASC
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(role, school)

    async def fetch_semester(self):
        query = '''
            SELECT fecha_comienzo, fecha_fin
            FROM ciclo_academico
            WHERE $1 >= fecha_comienzo AND
                  $1 <= fecha_fin
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(datetime.utcnow())


routes = {
    "students": {
        "list": StudentsList,
        "list/{display_amount:(?:10|25|all)}": StudentsList,
        "register-attendance": RegisterAttendance
    }
}
