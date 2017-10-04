from datetime import datetime
from aiohttp.web import View, json_response
from asyncpg.pool import PoolConnectionHolder

from utils.map import map_users
from utils.helpers import view as view, flatten


class StudentsList(View):
    @view('attendance.list')
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
                SELECT usuario.id, tipo_documento, nombres, apellidos, escuela,
                    COALESCE(
                        (SELECT CAST(COUNT(CASE WHEN asistio=true THEN 1 ELSE NULL END) / CAST(COUNT(*) AS FLOAT) * 100
                        AS INT)
                            FROM asistencia
                            RIGHT JOIN ciclo_academico
                                    ON ciclo_academico.fecha_comienzo <= asistencia.fecha_registro AND
                                       ciclo_academico.fecha_fin >= asistencia.fecha_registro
                       WHERE asistencia.alumno_id = usuario.id
                       HAVING COUNT(*) >= 1),
                    0) AS asistencia,
                    proyecto.id as id_proyecto, COALESCE(proyecto.titulo, 'No registrado') as titulo_proyecto,
                    (
                        SELECT COUNT(true)
                        FROM integrante_proyecto
                        WHERE integrante_proyecto.proyecto_id = proyecto.id
                    ) as integrantes_proyecto
                FROM usuario
                LEFT JOIN integrante_proyecto
                        ON integrante_proyecto.usuario_id = usuario.id
                LEFT JOIN proyecto
                        ON proyecto.id = integrante_proyecto.proyecto_id
                WHERE rol_id = $2 AND
                      escuela = $3 AND
                      nombres != '' AND
                      apellidos != '' AND
                      autorizado = TRUE AND
                      deshabilitado = FALSE
                LIMIT $4
            )
            SELECT id, tipo_documento, nombres, apellidos, asistencia, escuela,
                   CASE WHEN asistencia < $5 THEN true ELSE false END as peligro,
                   id_proyecto, titulo_proyecto,
                   CASE WHEN integrantes_proyecto < 2 THEN true ELSE false END as proyecto_solo
            FROM alumno
            ORDER BY apellidos ASC
        '''

        async with dbi.acquire() as connection:
            stmt = await connection.prepare(query)
            return await stmt.fetch(datetime.utcnow(), student_role_id, school, amount, danger)


class ReadAttendanceReport(View):
    async def get(self):
        student_id = int(self.request.match_info['student_id'])

        if 'school_term_id' in self.request.match_info:
            school_term_id = int(self.request.match_info['school_term_id'])
            school_term = await self.school_term_exists(school_term_id, self.request.app.db)

            if school_term:
                school_term = {'id': school_term_id}
                del school_term_id
            else:
                # Precondition failed, school term not found
                return json_response({}, status=412)
        else:
            school_term = await self.fetch_school_term(self.request.app.db)

            if not school_term:
                # Precondition failed, no school term registered as of now
                return json_response({}, status=412)

        schedules = await self.fetch_schedules(school_term['id'], self.request.app.db)
        attendances = dict()

        for schedule in schedules:
            attendances[schedule['id']] = await self.fetch_attendance_for_schedule(student_id,
                                                                                   schedule['id'],
                                                                                   self.request.app.db)

        result_data = flatten({
            'school_term': school_term,
            'schedules': schedules,
            'attendances': attendances
        })

        result_data['overall'] = {}

        _total = 0
        _total_times_attended = 0

        for _s, _a in result_data['attendances'].items():
            if _a:
                al_len, attended = 0, 0

                for _ar in _a:
                    al_len += 1
                    if _ar['asistio']:
                        attended += 1

                result_data['overall'][_s] = int(round(attended / al_len, 2) * 100)
                _total += al_len
                _total_times_attended += attended

        if result_data['overall']:
            result_data['overall']['average'] = int(round(_total_times_attended / _total, 2) * 100)

        return json_response(result_data, status=200)


    @staticmethod
    async def fetch_attendance_for_schedule(student: int, schedule: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT fecha_registro, asistio
            FROM asistencia
            WHERE alumno_id = $1 AND
                  horario_id = $2
        '''

        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetch(student, schedule)

    @staticmethod
    async def fetch_schedules(school_term: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT horario_profesor.id, profesor_id, nombres as profesor_nombres,
                   apellidos as profesor_apellidos, dia_clase, hora_comienzo,
                   hora_fin
            FROM horario_profesor
            LEFT JOIN usuario
                   ON usuario.id = profesor_id
            WHERE ciclo_id = $1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school_term)

    @staticmethod
    async def fetch_school_term(dbi: PoolConnectionHolder):
        query = '''
            SELECT id, fecha_comienzo, fecha_fin
            FROM ciclo_academico
            WHERE $1 >= fecha_comienzo AND
                  $1 <= fecha_fin
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(datetime.utcnow())

    @staticmethod
    async def school_term_exists(school_term: id, dbi: PoolConnectionHolder):
        query = '''
            SELECT true
            FROM ciclo_academico
            WHERE id = $1
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school_term)


class RegisterAttendance(View):
    @view('attendance.register')
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
        semester = await self.fetch_school_term(self.request.app.db)
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
                    INSERT INTO asistencia (alumno_id, profesor_id, fecha_registro, observacion, asistio)
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
    async def fetch_school_term(dbi: PoolConnectionHolder):
        query = '''
            SELECT id, fecha_comienzo, fecha_fin
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
        "register": RegisterAttendance,
        "student-report/{student_id:[1-9][0-9]*}": ReadAttendanceReport,
        "student-report/school-term-{school_term_id:[1-9][0-9]*}/{student_id:[1-9][0-9]*}": ReadAttendanceReport
    }
}
