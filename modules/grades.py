from typing import Union
from decimal import Decimal
from datetime import datetime
from asyncpg.pool import PoolConnectionHolder
from aiohttp.web import View, json_response, HTTPNotFound

from utils.map import map_users
from utils.validator import validator
from utils.helpers import view, flatten


class ClassGrades(View):
    """
        Esta vista se encarga de mostrar los reportes de notas de 1 ciclo académico.
        -----
        @view(...) es un decorador, se debe de pasar un string, el cual es la dirección al template que se va a
        mostrar.
        No es necesario ingresar la extensión, y preferible delimitar las carpetas con un .
        Ejemplo: Quiero que el método get nos muestre el template views/grades/class_report.html entonces ingreso
        @view('grades.class_report')
        -----
        Todos los metodos decorados por @view recibirán un argumento, este será el usuario y es un diccionario.
        -----
        Solo decorar los métodos que se están implementando, sea GET o POST, etc.
    """
    @view('grades.class_report')
    async def get(self, user: dict):
        # Primero necesitamos obtener el ciclo académico, sea el actual o uno que se ingresó en la uri
        if 'school_term' in self.request.match_info:  # Si se encuentra el parametro en la uri
            school_term_id = int(self.request.match_info['school_term'])  # Castear el valor a entero
            school_term = await self.school_term_exists(school_term_id, user['escuela'], self.request.app.db)

            del school_term_id

            if not school_term:  # Si el ciclo académico no se encontró
                raise HTTPNotFound  # Se levanta 404

        else:
            # Si no se pasó el parametro school_term en la uri, tratamos de obtener el ciclo académico actual
            school_term = await self.fetch_school_term(user['escuela'], self.request.app.db)

            if not school_term:
                # En este caso, no hay un ciclo académico registrado, pero no podemos tirar 404
                # pues no se pasó un parámetro de ciclo académico que no existe, informamos al usuario que no hay un
                # ciclo académico registrado, por lo tanto no hay data a mostrar.
                return {'message': 'No se encontró un ciclo académico registrado para este preciso momento. '
                                   'Puedes seleccionar un ciclo académico previo en el selector superior.'}

        students = await self.fetch_students(school_term['id'], self.request.app.db)

        if not students:
            # No se encontraron estudiantes, por lo tanto informamos al usuario que no se encontraron estudiantes
            # registrados para este ciclo académico
            return {'message': 'No hay estudiantes registrados para este ciclo académico aún.'}

        headers = await self.fetch_grade_headers(school_term['id'], self.request.app.db)

        if not headers:
            return {'message': 'No hay estructura de notas registrada, no hay notas por ver...'}

        header_group = list()

        def find_header_group(_group_name: str, _h_group: list) -> Union[int, bool]:
            for _i, _h in enumerate(_h_group):
                if isinstance(_h, list):
                    if _h[0] == _group_name:
                        return _i
            return False

        for header in headers:
            if not header['grupo']:
                header_group.append(header['descripcion'])
                continue

            _group_i = find_header_group(header['grupo'], header_group)

            if _group_i is False:
                header_group.append([header['grupo'], header['descripcion']])
            else:
                header_group[_group_i].append(header['descripcion'])

        headers = [*header_group]

        students = map_users(students)

        async def map_student(student: dict) -> dict:
            grades = await self.fetch_grades(school_term['id'], student['id'], self.request.app.db)
            grades = flatten(grades, {})
            grades = list(map(lambda x: float(x['valor']) if x['valor'] is not None else '-', grades))
            final_grade = await self.fetch_final_grade(school_term['id'], student['id'], self.request.app.db)

            if final_grade is None:
                final_grade = '-'

            grades.append(final_grade)

            return {**student, 'grades': grades}

        for _student_i, _student in enumerate(students):
            students[_student_i] = await map_student(_student)

        return {'headers': headers,
                'students': students}

    @staticmethod
    async def fetch_grade_headers(school_term: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT nota.descripcion, grupo_notas.descripcion as grupo
            FROM estructura_notas
            LEFT JOIN nota
                   ON nota.id = estructura_notas.nota_id
            LEFT JOIN grupo_notas
                   ON grupo_notas.id = nota.grupo_id
            WHERE ciclo_acad_id = $1
            ORDER BY nota.id ASC
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school_term)

    @staticmethod
    async def fetch_final_grade(school_term: int, student_id: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT valor
            FROM promedio_notas_ciclo
            WHERE ciclo_acad_id = $1 AND
                  estudiante_id = $2
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school_term, student_id)

    @staticmethod
    async def fetch_grades(school_term: int, student_id: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT nota_estudiante.valor
            FROM estructura_notas
            LEFT JOIN nota
                   ON nota.id = estructura_notas.nota_id
            LEFT JOIN nota_estudiante
                   ON nota_estudiante.nota_id = estructura_notas.nota_id AND
                      nota_estudiante.estudiante_id = $2
            WHERE ciclo_acad_id = $1
            ORDER BY nota.id ASC
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school_term, student_id)

    @staticmethod
    async def fetch_students(school_term: int, dbi: PoolConnectionHolder):
        # Obtener los estudiantes de un ciclo académico
        query = '''
            SELECT usuario.id, usuario.tipo_documento, usuario.nombres, usuario.apellidos, usuario.escuela
            FROM usuario
            RIGHT JOIN matricula
                    ON matricula.estudiante_id = usuario.id AND
                       matricula.ciclo_acad_id = $1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school_term)  # fetch = list

    @staticmethod
    async def school_term_exists(school_term: int, user_school: int, dbi: PoolConnectionHolder):
        # Retornará verdadero si existe el ciclo académico
        query = '''
            SELECT true
            FROM ciclo_academico
            WHERE id = $1
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school_term)  # fetchval = valor

    @staticmethod
    async def fetch_school_term(user_school: int, dbi: PoolConnectionHolder):
        # Retornará el ciclo académico en este preciso momento
        query = '''
            SELECT id, fecha_comienzo, fecha_fin
            FROM ciclo_academico
            WHERE $1 >= fecha_comienzo AND
                  $1 <= fecha_fin
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(datetime.utcnow())  # fetchrow = dict


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

        if not grades:
            return json_response({'messages': 'No hay estructura de notas registrada, no hay notas por ver...'},
                                 status=412)

        final_grade = await self.fetch_final_grade(school_term['id'], student['id'], self.request.app.db) or '-'

        result_data = flatten({
            'school_term': school_term,
            'student': student,
            'grades': grades,
            'final_grade': final_grade
        }, {})

        del school_term, student, grades

        grade_group = list()

        def find_grade(grade: dict) -> Union[int, bool]:
            for _i, _g in enumerate(grade_group):
                if isinstance(_g, list) and _g[0]['grupo'] == grade['grupo']:
                    return _i
            return False

        for grade in result_data['grades']:
            if grade['valor'] is None:
                grade['valor'] = '-'

            if grade['grupo'] is None:
                grade_group.append(grade)
            else:
                _g_i = find_grade(grade)

                if _g_i is False:
                    grade_group.append([grade])
                else:
                    grade_group[_g_i].append(grade)

        result_data['grades'] = grade_group

        return json_response(result_data)

    @staticmethod
    async def fetch_final_grade(school_term: int, student_id: int, dbi: PoolConnectionHolder):
        query = '''
                SELECT valor
                FROM promedio_notas_ciclo
                WHERE ciclo_acad_id = $1 AND
                      estudiante_id = $2
                LIMIT 1
            '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school_term, student_id)

    @staticmethod
    async def fetch_grades(school_term: int, student_id: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT estructura_notas.nota_id, grupo_notas.descripcion as grupo, nota.descripcion,
                   nota.porcentaje, nota_estudiante.valor
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


class AssignGrade(View):
    async def post(self):
        data = await self.request.post()
        
        if 'student_id' not in data and 'grade_id' not in data and 'score' not in data:
            return json_response({'error': 'No se envio la data necesaria.'}, status=400)  # Request malformado...

        errors = await self.validate(data)
        school_term = await self.fetch_school_term(self.request.app.db)

        if not school_term:
            return json_response({'error': 'No se encontro un ciclo academico para esta fecha'}, status=400)

        if errors:
            return json_response({'error': errors}, status=400)
        else:
            student_id = await self._get_student(school_term['id'], int(data['student_id']))

            if not student_id:
                return json_response({'error': 'No se encontro al estudiante'}, status=400)

            grade_id = await self._get_grade(school_term['id'], int(data['grade_id']))

            if not grade_id:
                return json_response({'error': 'No se encontro la nota que quiere registrar'}, status=400)

            if await self._assigned(grade_id, student_id):
                return json_response({'error': 'Esta nota ya ha sido asignada, no se puede cambiar'}, status=400)

            await self.create(grade_id, student_id, Decimal(data['score']))

        return json_response({'success': 'Se ha registrado la nota exitosamente'})

    async def validate(self, data: dict):
        return await validator.validate([
            ['ID de estudiante', data['student_id'], 'digits'],
            ['Nota', data['grade_id'], 'digits'],
            ['Puntaje', data['score'], 'len:1,4|numeric|custom', self._validate_score]
        ], self.request.app.db)

    async def create(self, grade_id: int, student_id: int, score: Decimal):
        query = '''
            INSERT INTO nota_estudiante (nota_id, estudiante_id, valor)
            VALUES ($1, $2, $3)
            RETURNING true
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(grade_id, student_id, score)

    async def _assigned(self, grade_id: int, student_id: int):
        query = '''
            SELECT true
            FROM nota_estudiante
            WHERE nota_estudiante.nota_id = $1 AND
                  nota_estudiante.estudiante_id = $2
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(grade_id, student_id) or False

    async def _get_grade(self, school_term: int, grade_id: int):
        query = '''
            SELECT estructura_notas.nota_id
            FROM estructura_notas
            WHERE estructura_notas.ciclo_acad_id = $1 AND
                  estructura_notas.nota_id = $2
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school_term, grade_id)

    async def _get_student(self, school_term: int, value: int) -> int:
        async with self.request.app.db.acquire() as connection:
            query = '''
                SELECT id
                FROM usuario
                RIGHT JOIN matricula
                        ON matricula.estudiante_id = usuario.id
                WHERE matricula.ciclo_acad_id = $1 AND
                      usuario.id = $2
            '''
            return await (await connection.prepare(query)).fetchval(school_term, value)

    @staticmethod
    async def _validate_score(name: str, value: str, *args):
        _value = float(value)

        if not 0 <= _value <= 20:
            return '{} debe de estar en el rango de 0 a 20'.format(name)

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
        'class-report': ClassGrades,
        'class-report/school-term-{school_term:[1-9][0-9]*}': ClassGrades,
        'student-report': {
            '{student_id:[1-9][0-9]*}': ReadGradeReport,
            'school-term-{school_term:[1-9][0-9]*}/{student_id:[1-9][0-9]*}': ReadGradeReport
        },
        'assign': AssignGrade
    }
}
