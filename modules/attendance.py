from datetime import datetime
from typing import Generator
from asyncpg.pool import PoolConnectionHolder
from aiohttp.web import View, json_response, HTTPUnauthorized

from utils.map import map_users
from utils.helpers import view, flatten, pass_user, permission_required, school_term_to_str


class StudentsList(View):
    @view('attendance.list')
    @permission_required('ver_listado_alumnos')
    async def get(self, user: dict):
        if 'school_term' in self.request.match_info:
            school_term_id = await self.get_school_term(user['escuela'], int(self.request.match_info['school_term']))
        else:
            school_term_id = await self.get_school_term(user['escuela'])

        if school_term_id is None:
            return {'school_term_has_not_begun': 'El ciclo académico no ha comenzado, tus acciones son limitadas'}

        # Estudiantes de escuela y tal
        students = await self.get_students(school_term_id, user['escuela'])
        students = map_users(students)

        # Notas disponibles para este ciclo
        dd_grades = await self.get_grades(school_term_id)

        # Ciclos académicos
        school_terms = await self.get_school_terms(user)

        current_school_term_id = school_term_id

        return {'students': students,
                'dd_grades': dd_grades,
                'school_terms': school_terms,
                'current_school_term_id': current_school_term_id}

    async def get_school_terms(self, user: dict):

        def _g(stl: list) -> Generator:
            for st in stl:
                yield st['id'], school_term_to_str(st)

        return list(_g(await self._get_school_terms(user['escuela'])))

    async def _get_school_terms(self, school: int):
        query = '''
            SELECT id, fecha_comienzo, fecha_fin
            FROM ciclo_academico
            WHERE ciclo_academico.escuela = $1
            ORDER BY id DESC
            LIMIT 10
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school)

    async def get_grades(self, school_term: int):
        query = '''
            SELECT estructura_notas.nota_id as id, nota.descripcion
            FROM estructura_notas
            LEFT JOIN nota
                   ON nota.id = estructura_notas.nota_id
            WHERE estructura_notas.ciclo_acad_id = $1
            ORDER BY estructura_notas.nota_id ASC
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school_term)

    async def get_school_term(self, school: int, school_term: int = None):
        if school_term is None:
            query = '''
                SELECT id
                FROM ciclo_academico
                WHERE $1 >= fecha_comienzo AND
                      $1 <= fecha_fin AND
                      escuela = $2
                LIMIT 1
            '''
        else:
            query = '''
                SELECT id
                FROM ciclo_academico
                WHERE id = $1 AND
                      escuela = $2
                LIMIT 1
            '''

        async with self.request.app.db.acquire() as connection:
            statement = await connection.prepare(query)
            if school_term is None:
                return await statement.fetchval(datetime.utcnow(), school)
            else:
                return await statement.fetchval(school_term, school)

    async def get_students(self, school_term: int, school: int, student_role_id: int = 1, danger: int = 63,
                           amount: int = 1000):
        query = '''
            WITH ciclo_academico AS (
                SELECT fecha_comienzo, fecha_fin
                FROM ciclo_academico
                WHERE id = $1
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
                        WHERE integrante_proyecto.proyecto_id = proyecto.id AND
                              integrante_proyecto.aceptado = true
                        LIMIT 1
                    ) as integrantes_proyecto
                FROM usuario
                LEFT JOIN integrante_proyecto
                        ON integrante_proyecto.usuario_id = usuario.id AND
                           integrante_proyecto.aceptado = true
                LEFT JOIN proyecto
                        ON proyecto.id = integrante_proyecto.proyecto_id
                INNER JOIN matricula
                        ON matricula.estudiante_id = usuario.id AND
                           matricula.ciclo_acad_id = $1
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

        async with self.request.app.db.acquire() as connection:
            stmt = await connection.prepare(query)
            return await stmt.fetch(school_term, student_role_id, school, amount, danger)


class ReadAttendanceReport(View):
    @pass_user
    async def get(self, user: dict):
        # Validar permisos...
        if not user['permissions']['ver_reportes_personales'] and self.request.match_info['student_id'] == 'my-own':
            raise HTTPUnauthorized
        elif user['permissions']['ver_reportes_personales'] and self.request.match_info['student_id'] != 'my-own':
            raise HTTPUnauthorized
        elif not user['permissions']['ver_listado_alumnos'] and not user['permissions']['ver_reportes_personales']:
            raise HTTPUnauthorized

        if self.request.match_info['student_id'] == 'my-own':
            student_id = user['id']
        else:
            student_id = int(self.request.match_info['student_id'])

        if 'school_term_id' in self.request.match_info:
            school_term_id = int(self.request.match_info['school_term_id'])
            school_term = await self.school_term_exists(school_term_id, user['escuela'], self.request.app.db)

            if school_term:
                school_term = {'id': school_term_id}
                del school_term_id
            else:
                # No se encontró ciclo académico
                return json_response({'message': 'Ciclo académico no encontrado'}, status=400)
        else:
            school_term = await self.fetch_school_term(user['escuela'], self.request.app.db)

            if not school_term:
                # No hay ciclo académico registrado para esta fecha
                return json_response({'message': 'No se encontró un ciclo académico para esta fecha'}, status=400)

        schedules = await self.fetch_schedules(school_term['id'], self.request.app.db)

        if not schedules:
            return json_response({'message': 'No hay horarios disponibles'}, status=400)

        attendances = dict()

        for schedule in schedules:
            attendances[schedule['id']] = await self.fetch_attendance_for_schedule(student_id,
                                                                                   schedule['id'],
                                                                                   self.request.app.db)

        result_data = flatten({
            'school_term': school_term,
            'schedules': schedules,
            'attendances': attendances
        }, {'with_time': True, 'long': True})

        result_data['overall'] = {}

        total_amount, attended = 0, 0

        for _i, _s in enumerate(result_data['schedules']):
            _ni = _i + 1
            result_data['overall'][_ni] = list()

            for _, _s_wa in result_data['attendances'].items():
                if _s_wa:
                    for _a in _s_wa:
                        if _a['horario_id'] == _s['id']:
                            total_amount += 1
                            if _a['asistio']:
                                attended += 1
                                result_data['overall'][_ni].append(1)
                            else:
                                result_data['overall'][_ni].append(0)

        for _k, _overall in result_data['overall'].items():
            if _overall:
                result_data['overall'][_k] = int(round(sum(_overall) / len(_overall), 2) * 100)
            else:
                result_data['overall'][_k] = 0

        if attended != 0 and total_amount != 0:
            result_data['overall']['average'] = int(round(attended / total_amount, 2) * 100)
        else:
            result_data['overall']['average'] = 0

        return json_response(result_data, status=200)


    @staticmethod
    async def fetch_attendance_for_schedule(student: int, schedule: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT horario_id, fecha_registro, asistio
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
            ORDER BY usuario.nombres ASC, usuario.apellidos ASC, dia_clase ASC, hora_comienzo ASC
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school_term)

    @staticmethod
    async def fetch_school_term(school: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT id, fecha_comienzo, fecha_fin
            FROM ciclo_academico
            WHERE $1 >= fecha_comienzo AND
                  $1 <= fecha_fin AND
                  escuela = $2
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(datetime.utcnow(), school)

    @staticmethod
    async def school_term_exists(school_term: int, school: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT true
            FROM ciclo_academico
            WHERE id = $1 AND
                  escuela = $2
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school_term, school)


class RegisterAttendance(View):
    @view('attendance.register')
    @permission_required('registrar_asistencia')
    async def get(self, user: dict):
        students = await self.fetch_students(user['escuela'], self.request.app.db)
        schedule = await self.fetch_teacher_schedule(user['id'], self.request.app.db)

        return {'schedule': schedule,
                'students': students}

    @view('attendance.register')
    @permission_required('registrar_asistencia')
    async def post(self, user: dict):
        students = await self.fetch_students(user['escuela'], self.request.app.db)
        schedule = await self.fetch_teacher_schedule(user['id'], self.request.app.db)

        if not schedule:
            raise ValueError

        data = dict(await self.request.post())
        data = await self.convert_data(data, students)
        data = await self.format_data(data, schedule)

        result = await self.register_attendance(data, self.request.app.db)

        if isinstance(result, list):
            result = True

        return {'schedule': schedule,
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
    async def format_data(data: list, schedule: dict) -> list:
        current_time = datetime.utcnow()
        return [[s[0], schedule['id'], current_time, s[1], s[2]] for s in data]

    @staticmethod
    async def register_attendance(data: list, dbi: PoolConnectionHolder):
        async with dbi.acquire() as connection:
            async with connection.transaction():
                query = '''
                    INSERT INTO asistencia (alumno_id, horario_id, fecha_registro, observacion, asistio)
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
    async def fetch_teacher_schedule(teacher: int, dbi: PoolConnectionHolder):
        query = '''
            WITH ciclo_acad AS (
                SELECT id
                FROM ciclo_academico
                WHERE $1 >= fecha_comienzo AND
                      $1 <= fecha_fin
                LIMIT 1
            )
            SELECT horario_profesor.id, ciclo_id, profesor_id, dia_clase, hora_comienzo, hora_fin
            FROM horario_profesor
            LEFT JOIN ciclo_academico
                   ON ciclo_academico.id = horario_profesor.ciclo_id
            WHERE ciclo_id = (SELECT id FROM ciclo_acad) AND
                  profesor_id = $2
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(datetime.utcnow(), teacher)


routes = {
    'students': {
        'list': StudentsList,
        'list/school-term-{school_term:[1-9][0-9]*}': StudentsList
    },
    'attendance': {
        'register': RegisterAttendance,
        'student-report/{student_id:(?:[1-9][0-9]*|my-own)}': ReadAttendanceReport,
        'student-report/school-term-{school_term_id:[1-9][0-9]*}/{student_id:[1-9][0-9]*}': ReadAttendanceReport
    }
}
