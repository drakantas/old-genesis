from datetime import datetime
from aiohttp.web import View, json_response
from asyncpg.pool import PoolConnectionHolder

from utils.helpers import view as view, flatten


class ReadGradeReport(View):
    async def get(self):
        student_id = int(self.request.match_info['student_id'])

        if 'school_term' in self.request.match_info:
            school_term_id = int(self.request.match_info['school_term'])
            school_term = await self.school_term_exists(school_term_id, self.request.app.db)

            if not school_term:
                return json_response({'message': 'Ciclo académico no encontrado'}, status=404)
            else:
                # Se encontró el ciclo académico
                school_term = {'id': school_term_id}
        else:
            school_term = await self.fetch_school_term(self.request.app.db)

            if not school_term:
                return json_response({'message': 'No se encontró un ciclo académico para esta fecha'}, status=412)

        student = await self.fetch_student(student_id, self.request.app.db)

        if not student:
            return json_response({'message': 'No se encontró al estudiante'}, status=404)

        grades = await self.fetch_grades(school_term['id'], student['id'], self.request.app.db)

        result_data = flatten({
            'school_term': school_term,
            'student': student,
            'grades': grades
        }, {})

        del school_term, student, grades

        grade_groups = dict()

        for grade in result_data['grades']:
            if grade['grupo'] is None:
                grade_groups[grade['nota_id']] = grade
                continue

            if grade['grupo'] not in grade_groups:
                grade_groups[grade['grupo']] = [grade]
            else:
                grade_groups[grade['grupo']].append(grade)

        result_data['grades'] = grade_groups

        return json_response(result_data)

    @staticmethod
    async def fetch_grade_group(group_id: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT descripcion
            FROM grupo_notas
            WHERE id = $1
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(group_id)

    @staticmethod
    async def fetch_grades(school_term: int, student_id: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT estructura_notas.nota_id, grupo_notas.descripcion as grupo, nota.descripcion, nota.porcentaje, nota_estudiante.valor
            FROM estructura_notas
            LEFT JOIN nota
                   ON nota.id = estructura_notas.nota_id
            LEFT JOIN grupo_notas
                   ON grupo_notas.id = nota.grupo_id
            LEFT JOIN nota_estudiante
                   ON nota_estudiante.nota_id = estructura_notas.nota_id AND
                      nota_estudiante.estudiante_id = $2
            WHERE ciclo_acad_id = $1
            ORDER BY nota.id ASC
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school_term, student_id)

    @staticmethod
    async def fetch_student(student_id: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT id, nombres, apellidos
            FROM usuario
            WHERE id = $1 AND
                  rol_id = 1 AND
                  autorizado = TRUE
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(student_id)

    @staticmethod
    async def school_term_exists(school_term: int, dbi: PoolConnectionHolder):
        query = '''
                SELECT true
                FROM ciclo_academico
                WHERE id = $1
                LIMIT 1
            '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school_term)

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


routes = {
    'grades': {
        'student-report': {
            '{student_id:[1-9][0-9]*}': ReadGradeReport,
            'school-term-{school_term:[1-9][0-9]*}/{student_id:[1-9][0-9]*}': ReadGradeReport
        }
    }
}
