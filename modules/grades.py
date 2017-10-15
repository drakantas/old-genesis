from decimal import Decimal
from datetime import datetime
from typing import Union, Generator
from aiohttp.web import View, json_response, HTTPNotFound

from utils.validator import validator
from utils.map import map_users, parse_data_key
from utils.helpers import view, flatten, pass_user
from modules.attendance import same_year_st, diff_year_str


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
            school_term = await self.school_term_exists(school_term_id, user['escuela'])

            if not school_term:  # Si el ciclo académico no se encontró
                raise HTTPNotFound  # Se levanta 404
            else:
                school_term = {
                    'id': school_term_id
                }

                del school_term_id

        else:
            # Si no se pasó el parametro school_term en la uri, tratamos de obtener el ciclo académico actual
            school_term = await self.fetch_school_term(user['escuela'])

            if not school_term:
                # En este caso, no hay un ciclo académico registrado, pero no podemos tirar 404
                # pues no se pasó un parámetro de ciclo académico que no existe, informamos al usuario que no hay un
                # ciclo académico registrado, por lo tanto no hay data a mostrar.
                return {'message': 'No se encontró un ciclo académico registrado para este preciso momento. '
                                   'Puedes seleccionar un ciclo académico previo en el selector superior.',
                        'school_terms': await self.get_school_terms(user),
                        'current_school_term_id': school_term['id']}

        students = await self.fetch_students(school_term['id'])

        if not students:
            # No se encontraron estudiantes, por lo tanto informamos al usuario que no se encontraron estudiantes
            # registrados para este ciclo académico
            return {'message': 'No hay estudiantes registrados para este ciclo académico aún.',
                    'school_terms': await self.get_school_terms(user),
                    'current_school_term_id': school_term['id']}

        headers = await self.fetch_grade_headers(school_term['id'])

        if not headers:
            return {'message': 'No hay estructura de notas registrada, no hay notas por ver...',
                    'school_terms': await self.get_school_terms(user),
                    'current_school_term_id': school_term['id']}

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
            grades = await self.fetch_grades(school_term['id'], student['id'])
            grades = flatten(grades, {})
            grades = list(map(lambda x: float(x['valor']) if x['valor'] is not None else '-', grades))
            final_grade = await self.fetch_final_grade(school_term['id'], student['id'])

            if final_grade is None:
                final_grade = '-'

            grades.append(final_grade)

            return {**student, 'grades': grades}

        for _student_i, _student in enumerate(students):
            students[_student_i] = await map_student(_student)

        return {'headers': headers,
                'students': students,
                'school_terms': await self.get_school_terms(user),
                'current_school_term_id': school_term['id']}

    async def fetch_grade_headers(self, school_term: int):
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
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school_term)

    async def fetch_final_grade(self, school_term: int, student_id: int):
        query = '''
            SELECT valor
            FROM promedio_notas_ciclo
            WHERE ciclo_acad_id = $1 AND
                  estudiante_id = $2
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school_term, student_id)

    async def fetch_grades(self, school_term: int, student_id: int):
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
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school_term, student_id)

    async def fetch_students(self, school_term: int):
        # Obtener los estudiantes de un ciclo académico
        query = '''
            SELECT usuario.id, usuario.tipo_documento, usuario.nombres, usuario.apellidos, usuario.escuela
            FROM usuario
            INNER JOIN matricula
                    ON matricula.estudiante_id = usuario.id AND
                       matricula.ciclo_acad_id = $1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school_term)  # fetch = list

    async def school_term_exists(self, school_term: int, school: int):
        # Retornará verdadero si existe el ciclo académico
        query = '''
            SELECT true
            FROM ciclo_academico
            WHERE id = $1 AND
                  escuela = $2
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school_term, school)  # fetchval = valor

    async def fetch_school_term(self, school: int):
        # Retornará el ciclo académico en este preciso momento
        query = '''
            SELECT id, fecha_comienzo, fecha_fin
            FROM ciclo_academico
            WHERE $1 >= fecha_comienzo AND
                  $1 <= fecha_fin AND
                  escuela = $2
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(datetime.utcnow(), school)  # fetchrow = dict

    async def get_school_terms(self, user: dict):

        def _g(stl: list) -> Generator:
            for st in stl:
                yield st['id'], self.school_term_to_str(st)

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

    @staticmethod
    def school_term_to_str(school_term: dict) -> str:
        if school_term['fecha_comienzo'].year == school_term['fecha_fin'].year:
            return same_year_st.format(year=school_term['fecha_comienzo'].year,
                                       month1=parse_data_key(school_term['fecha_comienzo'].month, 'months'),
                                       month2=parse_data_key(school_term['fecha_fin'].month, 'months'))

        return diff_year_str.format(year1=school_term['fecha_comienzo'].year,
                                    month1=parse_data_key(school_term['fecha_comienzo'].month, 'months'),
                                    year2=school_term['fecha_fin'].year,
                                    month2=parse_data_key(school_term['fecha_fin'].month, 'months'))


class ReadGradeReport(View):
    @pass_user
    async def get(self, user: dict):
        student_id = int(self.request.match_info['student_id'])

        if 'school_term' in self.request.match_info:
            school_term_id = int(self.request.match_info['school_term'])
            school_term = await self.school_term_exists(school_term_id, user['escuela'])

            if not school_term:
                return json_response({'message': 'Ciclo académico no encontrado'}, status=400)
            else:
                # Se encontró el ciclo académico
                school_term = {'id': school_term_id}
        else:
            school_term = await self.fetch_school_term(user['escuela'])

            if not school_term:
                return json_response({'message': 'No se encontró un ciclo académico para esta fecha'}, status=400)

        student = await self.fetch_student(student_id)

        if not student:
            return json_response({'message': 'No se encontró al estudiante'}, status=400)

        grades = await self.fetch_grades(school_term['id'], student['id'])

        if not grades:
            return json_response({'message': 'No hay estructura de notas registrada, no hay notas por ver...'},
                                 status=400)

        final_grade = await self.fetch_final_grade(school_term['id'], student['id']) or '-'

        result_data = flatten({
            'school_term': school_term,
            'student': student,
            'grades': grades,
            'final_grade': final_grade
        }, {})

        del school_term, student, grades

        grade_group = list()

        def find_grade(_grade: dict) -> Union[int, bool]:
            for _i, _g in enumerate(grade_group):
                if isinstance(_g, list) and _g[0]['grupo'] == _grade['grupo']:
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

    async def fetch_final_grade(self, school_term: int, student_id: int):
        query = '''
                SELECT valor
                FROM promedio_notas_ciclo
                WHERE ciclo_acad_id = $1 AND
                      estudiante_id = $2
                LIMIT 1
            '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school_term, student_id)

    async def fetch_grades(self, school_term: int, student_id: int):
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
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school_term, student_id)

    async def fetch_student(self, student_id: int):
        query = '''
            SELECT id, nombres, apellidos
            FROM usuario
            WHERE id = $1 AND
                  rol_id = 1 AND
                  autorizado = TRUE
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(student_id)

    async def school_term_exists(self, school_term: int, school: int):
        query = '''
                SELECT true
                FROM ciclo_academico
                WHERE id = $1 AND
                      escuela = $2
                LIMIT 1
            '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school_term, school)

    async def fetch_school_term(self, school: int):
        query = '''
                SELECT id, fecha_comienzo, fecha_fin
                FROM ciclo_academico
                WHERE $1 >= fecha_comienzo AND
                      $1 <= fecha_fin AND
                      escuela = $2
                LIMIT 1
            '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(datetime.utcnow(), school)


class AssignGrade(View):
    @pass_user
    async def post(self, user: dict):
        data = await self.request.post()

        if 'student_id' not in data or 'grade_id' not in data or 'score' not in data:
            return json_response({'error': 'No se envio la data necesaria.'}, status=400)  # Request malformado...

        errors = await self.validate(data)
        school_term = await self.fetch_school_term(user['escuela'])

        if not school_term:
            return json_response({'error': 'No se encontro un ciclo academico para esta fecha'}, status=400)

        now = datetime.utcnow()

        # Un poco over the top, considerando que la consulta no retornará ningún ciclo académico si el tiempo actual
        # No se encuentra en un rango de algún ciclo académico de la escuela...
        if school_term['fecha_comienzo'] > now:
            return json_response({'error': 'Todavía no puedes asignar notas para este ciclo académico'}, status=400)
        elif school_term['fecha_fin'] <= now:
            return json_response({'error': 'Este ciclo académico ya ha culminado'}, status=400)

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
        query = '''
            SELECT id
            FROM usuario
            RIGHT JOIN matricula
                    ON matricula.estudiante_id = usuario.id
            WHERE matricula.ciclo_acad_id = $1 AND
                  usuario.id = $2
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school_term, value)

    async def fetch_school_term(self, school: int):
        query = '''
                SELECT id, fecha_comienzo, fecha_fin
                FROM ciclo_academico
                WHERE $1 >= fecha_comienzo AND
                      $1 <= fecha_fin AND
                      escuela = $2
                LIMIT 1
            '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(datetime.utcnow(), school)

    @staticmethod
    async def _validate_score(name: str, value: str, *args):
        _value = float(value)

        if not 0 <= _value <= 20:
            return '{} debe de estar en el rango de 0 a 20'.format(name)


class UpdateGrade(View):
    async def post(self):
        if 'grade_id' not in self.request.match_info or 'student_id' not in self.request.match_info:
            raise HTTPNotFound

        grade_id = int(self.request.match_info['grade_id'])
        student_id = int(self.request.match_info['student_id'])

        grade = await self.fetch_grade(grade_id, student_id)

        if not grade:
            return json_response({'message': 'No se encontró la nota ingresada'}, status=400)

        now = datetime.utcnow()

        if not grade['fecha_comienzo'] <= now <= grade['fecha_fin']:
            return json_response({'message': 'No se puede actualizar las notas de un ciclo académico ya culminado o'
                                             'que recién va a comenzar'}, status=400)

        final_grade_exists = await self.fetch_final_grade(student_id, grade['ciclo_acad_id']) or False

        if final_grade_exists:
            return json_response({'message': 'No puedes actualizar esta nota porque ya se generó el promedio'
                                             'final del curso'}, status=400)

        data = await self.request.post()  # Coger data

        if 'score' not in data:
            return json_response({'message': 'No se envió la data apropiada'}, status=400)

        errors = await self.validate(data)

        if errors:
            return json_response({'message': errors}, status=400)

        await self.update(grade_id, student_id, Decimal(data['score']))

        return json_response({'message': 'Se actualizó la nota exitosamente'})

    async def validate(self, data: dict) -> Union[list, None]:
        return await validator.validate([
                ['Puntaje', data['score'], 'len:1,4|numeric|custom', self._validate_score]
        ], self.request.app.db)

    async def update(self, grade: int, student: int, score: Decimal):
        query = '''
            UPDATE nota_estudiante
            SET valor = $3
            WHERE nota_id = $1 AND
                  estudiante_id = $2
        '''
        async with self.request.app.db.acquire() as connection:
            return await connection.execute(query, grade, student, score)

    async def fetch_final_grade(self, student: int, school_term: int):
        query = '''
            SELECT true
            FROM promedio_notas_ciclo
            WHERE promedio_notas_ciclo.ciclo_acad_id = $1 AND
                  promedio_notas_ciclo.estudiante_id = $2
            LIMIT 1;
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(school_term, student)

    async def fetch_grade(self, grade: int, student: int):
        query = '''
            SELECT nota_estudiante.nota_id, nota_estudiante.valor,
                   nota.descripcion, ciclo_academico.id as ciclo_acad_id,
                   ciclo_academico.fecha_comienzo, ciclo_academico.fecha_fin
            FROM nota_estudiante
            LEFT JOIN estructura_notas
                   ON estructura_notas.nota_id = nota_estudiante.nota_id
            LEFT JOIN nota
                   ON nota.id = nota_estudiante.nota_id
            LEFT JOIN ciclo_academico
                   ON ciclo_academico.id = estructura_notas.ciclo_acad_id
            WHERE nota_estudiante.nota_id = $1 AND
                  nota_estudiante.estudiante_id = $2
            LIMIT 1;
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(grade, student)

    async def fetch_current_school_term(self, school: int):
        query = '''
            SELECT id, fecha_comienzo, fecha_fin
            FROM ciclo_academico
                WHERE $1 >= fecha_comienzo AND
                      $1 <= fecha_fin AND
                      escuela = $2
                LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(datetime.utcnow(), school)

    @staticmethod
    async def _validate_score(name: str, value: str, *args):
        _value = float(value)

        if not 0 <= _value <= 20:
            return '{} debe de estar en el rango de 0 a 20'.format(name)


class CreateGradingStructure(View):
    @view('grades.create_structure')
    async def get(self, user: dict):
        return {}

    @view('grades.create_structure')
    async def post(self, user: dict):
        return {}


routes = {
    'grades': {
        'class-report': ClassGrades,
        'class-report/school-term-{school_term:[1-9][0-9]*}': ClassGrades,
        'student-report': {
            '{student_id:[1-9][0-9]*}': ReadGradeReport,
            'school-term-{school_term:[1-9][0-9]*}/{student_id:[1-9][0-9]*}': ReadGradeReport
        },
        'assign': AssignGrade,
        'update/{grade_id:[1-9][0-9]*}/student-{student_id:[1-9][0-9]*}': UpdateGrade
    }
}
