import re
from typing import Union
from decimal import Decimal
from aiohttp.web import View, HTTPFound
from datetime import datetime, timedelta
from asyncpg.pool import PoolConnectionHolder

from utils.map import map_users
from utils.validator import validator
from utils.helpers import view, humanize_datetime, permission_required, pass_user


# Muy malo...
MM_DD_YYYY_FORMAT = r'(?:0[1-9]|10|11|12)\/[0-3][0-9]\/20[0-9]{2}'
MM_DD_YYYY = re.compile(MM_DD_YYYY_FORMAT)
SCHEDULE_KEY_FORMAT = r'schedule_([0-9]+)_(?:teacher|day|start_time|end_time)'
SCHEDULE_KEY = re.compile(SCHEDULE_KEY_FORMAT)
TIME_FORMAT = r'(?:1|2|3|4|5|6|7|8|9|10|11|12):[0-5][0-9] (?:AM|PM)'
TIME = re.compile(TIME_FORMAT)
GRADES_GROUP = r'group_([1-9][0-9]*)'
GRADES_GROUP = re.compile(GRADES_GROUP)
GRADE = r'group_([1-9][0-9]*)_grade_([1-9][0-9]*)'
GRADE = re.compile(GRADE)

df = '%m/%d/%Y'


class CreateSchoolTerm(View):
    @view('school_term.create')
    @permission_required('gestionar_asistencias')
    async def get(self, user: dict):
        teachers = map_users(await self.fetch_teachers(user['escuela'], 2, self.request.app.db))

        return {'teachers': teachers,
                'today': humanize_datetime(datetime.utcnow(), with_time=False)}

    @view('school_term.create')
    @permission_required('gestionar_asistencias')
    async def post(self, user: dict):
        teachers = map_users(await self.fetch_teachers(user['escuela'], 2, self.request.app.db))

        result_data = {'teachers': teachers,
                       'today': humanize_datetime(datetime.utcnow(), with_time=False)}

        data = await self.request.post()
        errors = await self.validate(data)

        if errors:
            result_data['errors'] = errors
        else:
            start_date = datetime.strptime(data['beginning_date'], df)
            end_date = datetime.strptime(data['ending_date'], df)

            _e = []

            if await self.fetch_school_term(start_date, user['escuela'], self.request.app.db):
                _e.append('La fecha de comienzo ya se encuentra en el rango que abarca otro ciclo académico')

            if await self.fetch_school_term(end_date, user['escuela'], self.request.app.db):
                _e.append('La fecha de culminación ya se encuentra en el rango que abarca otro ciclo académico')

            if _e:
                result_data['errors'] = _e
            else:
                validation_groups = await self._get_validation_groups(data)
                if not validation_groups:
                    if 'errors' not in result_data:
                        result_data['errors'] = list()

                    result_data['errors'].append('No se enviaron los campos de horario correctamente')
                else:
                    validation_rules = await self._build_validation_groups(validation_groups, data)

                    _validation_errors = await validator.validate(validation_rules, self.request.app.db)

                    if _validation_errors:
                        result_data['errors'] = _validation_errors
                    else:
                        await self.create(validation_groups, data, user['escuela'], self.request.app.db)
                        result_data['success'] = 'Se ha creado el ciclo académico exitosamente'

            del _e

        return result_data

    async def validate(self, data: dict):
        return await validator.validate([
            ['Fecha comienzo', data['beginning_date'], 'len:10|custom', self._validate_date],
            ['Fecha de culminación', data['ending_date'], 'len:10|custom', self._validate_date]
        ], self.request.app.db)

    async def create(self, groups: list, data: dict, school: int, dbi: PoolConnectionHolder):
        query = '''
            WITH ciclo_acad AS (
                INSERT INTO ciclo_academico (fecha_comienzo, fecha_fin, escuela)
                VALUES ($1, $2, $3)
                RETURNING id
            )
            
            INSERT INTO horario_profesor (ciclo_id, profesor_id, dia_clase, hora_comienzo, hora_fin)
            VALUES {values}            
        '''

        values = ''
        for group in groups:
            values = values + await self._build_group_query(group, data)

        values = values[:-2]
        query = query.format(values=values)

        async with dbi.acquire() as connection:
            async with connection.transaction():
                await connection.execute(query,
                                         datetime.strptime(data['beginning_date'], df),
                                         datetime.strptime(data['ending_date'], df),
                                         school)

    async def _build_group_query(self, group: list, data: dict) -> str:
        query = '''((SELECT id FROM ciclo_acad), {0}, {1}, {2}, {3}), '''.format(int(data[group[0]]),
                                                                               int(data[group[1]]),
                                                                               self._parse_time(data[group[2]]),
                                                                               self._parse_time(data[group[3]]))
        return query

    @staticmethod
    def _parse_time(time: str) -> int:
        _time = 0

        if time.endswith('PM'):
            _time += 1200

        time = time[:-3]
        time = time.replace(':', '')

        _time += int(time)

        return _time


    @staticmethod
    async def _get_validation_groups(data: dict) -> Union[list, bool]:
        groups = list()

        def _get_group(id_: int, groups_: list) -> list:
            str_id = str(id_)
            _group = []

            for e in groups_:
                if e.startswith('schedule_' + str_id):
                    _group.append(e)

            return _group

        for k in data.keys():
            if SCHEDULE_KEY.fullmatch(k):
                groups.append(k)

        g_len = len(groups)

        # Los grupos no se enviaron completamente...
        if g_len % 4 != 0:
            return False

        g_amount = int(g_len / 4)
        _groups = list()

        for g_id in range(g_amount):
            group = _get_group(g_id, groups)

            if len(group) != 4:
                return False  # La data es incorrecta...

            _groups.append(group)

        groups = [*_groups]

        del _groups

        return groups or False

    async def _build_validation_groups(self, groups: list, data: dict) -> list:
        def _build_group(group: list) -> list:
            _id = SCHEDULE_KEY.fullmatch(group[0]).group(1)
            _group = list()

            for e in group:
                if e.endswith('teacher'):
                    _group.append(['Profesor {}'.format(_id), data[e], 'custom', self._validate_teacher])
                elif e.endswith('day'):
                    _group.append(['Día {}'.format(_id), data[e], 'digits|len:1|custom', self._validate_day])
                elif e.endswith('start_time'):
                    _group.append(['Fecha de comienzo de horario {}'.format(_id), data[e], 'len:7,8|custom', self._validate_time])
                elif e.endswith('end_time'):
                    _group.append(['Fecha de culminación de horario {}'.format(_id), data[e], 'len:7,8|custom', self._validate_time])
                else:
                    raise ValueError

            return _group

        groups = list(map(_build_group, groups))
        rules = list()

        for g in groups:
            for r in g:
                rules.append(r)

        return rules

    @staticmethod
    async def _validate_time(name: str, value: str, *args):
        if not TIME.fullmatch(value):
            return '{name} no es una hora correcta'.format(name=name)

    @staticmethod
    async def _validate_day(name: str, value: str, *args):
        _v = int(value)

        if not 0 <= _v <= 6:
            return 'El día seleccionado en {name} no está en el rango de 0 a 6'.format(name=name)

    @staticmethod
    async def _validate_teacher(name: str, value: str, pos: int, elems: list, dbi: PoolConnectionHolder):
        query = '''
            SELECT true
            FROM usuario
            WHERE id = $1 AND
                  rol_id = 2 AND
                  deshabilitado = FALSE
            LIMIT 1
        '''

        async with dbi.acquire() as connection:
            teacher_exists = await (await connection.prepare(query)).fetchval(int(value))

        if not teacher_exists:
            return 'El profesor seleccionado en {name} no fue encontrado o está deshabilitado'.format(name=name)

    @staticmethod
    async def _validate_date(name: str, value: str, *args):
        if not MM_DD_YYYY.fullmatch(value):
            return '{name} no tiene el formato correcto. Día/Mes/Año'.format(name=name)

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
    async def fetch_school_term(date: datetime, school: int, dbi: PoolConnectionHolder):
        query = '''
            SELECT id
            FROM ciclo_academico
            WHERE $1 >= fecha_comienzo AND
                  $1 <= fecha_fin AND
                  escuela = $2
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(date, school)


class DisableStudents(View):
    @pass_user
    @permission_required('mantener_usuarios')
    async def get(self, user: dict):
        try:
            await self.update(user['escuela'])
        except:
            pass

        raise HTTPFound('/users/list')

    async def update(self, school: int):
        async with self.request.app.db.acquire() as connection:
            return await connection.execute('''
                WITH ciclo_academico AS (
                    SELECT ciclo_academico.id
                    FROM ciclo_academico
                    WHERE ciclo_academico.fecha_comienzo <= $1 AND
                          ciclo_academico.fecha_fin >= $1 AND
                          ciclo_academico.escuela = $2
                )
                
                UPDATE usuario
                SET deshabilitado = true
                FROM matricula
                WHERE matricula.ciclo_acad_id = (SELECT id FROM ciclo_academico) AND
                      matricula.estudiante_id = usuario.id AND
                      usuario.rol_id = 1
            ''', datetime.utcnow() - timedelta(hours=5), school)


class CreateGradingStructure(View):
    @view('school_term.create_structure')
    @permission_required('gestionar_notas')
    async def get(self, user: dict):
        return {'can_create_structure': await self.can_create_structure(user['escuela'])}

    @view('school_term.create_structure')
    @permission_required('gestionar_notas')
    async def post(self, user: dict):
        display_data = {
            'can_create_structure': await self.can_create_structure(user['escuela']),
        }

        if not display_data['can_create_structure']:
            display_data['error'] = 'No puedes registrar una estructura de notas porque ya se registró una.'
            return display_data

        school_term = await self.fetch_current_school_term(user['escuela'])

        if not school_term:
            display_data['error'] = 'No hay un ciclo académico registrado.'
            return display_data

        data = await self.request.post()

        if not data:
            display_data['error'] = 'No se enviaron los parámetros necesarios...'
            return display_data

        try:
            data = await self.get_data(data)
        except ValueError:
            display_data['error'] = 'No se enviaron los parámetros necesarios...'
            return display_data

        errors = await self.validate(data)

        if errors[0]:
            display_data['errors'] = errors[0]
            return display_data

        if errors[1][0] > 100:
            display_data['error'] = 'El porcentaje total debe de ser 100, no más.'
            return display_data

        await self.create(data, school_term['id'])

        display_data.update({
            'success': 'Se ha registrado la estructura de notas exitosamente',
            'can_create_structure': await self.can_create_structure(user['escuela'])
        })

        return display_data

    async def validate(self, data: dict):
        rules = list()
        percentage = [0.0]

        for k, v in data.items():
            rules.append(['Nombre de grupo {}'.format(k), v['name'], 'len:6,32'])

            for i, grade in enumerate(v['grades']):
                rules.append(['Nombre de nota {} de grupo {}'.format(i + 1, k), grade[0], 'len:2,32'])
                rules.append(['Porcentaje de nota {} de grupo {}'.format(i + 1, k),
                              grade[1], 'numeric|len:1,4|custom', self._hacky_sum, percentage])

        return await validator.validate([
            *rules
        ], self.request.app.db), percentage

    async def create(self, data: dict, school_term: int):
        async with self.request.app.db.acquire() as connection:
            async with connection.transaction():
                for k, v in data.items():
                    group = await connection.fetchval('''
                        INSERT INTO grupo_notas (descripcion)
                        VALUES ($1)
                        RETURNING id
                    ''', v['name'])

                    for grade in enumerate(v['grades']):
                        _grade = await connection.fetchval('''
                            INSERT INTO nota (grupo_id, descripcion, porcentaje)
                            VALUES ($1, $2, $3)
                            RETURNING id
                        ''', group, grade[1][0], Decimal(grade[1][1]))

                        await connection.execute('''
                            INSERT INTO estructura_notas (ciclo_acad_id, nota_id)
                            VALUES ($1, $2)
                        ''', school_term, _grade)



    @staticmethod
    async def _hacky_sum(name: str, value: str, pos: int, elems: list, dbi: PoolConnectionHolder,
                                    percentage: list):
        percentage[0] += float(value)

    @staticmethod
    async def get_data(data: dict) -> dict:
        _data = dict()

        for k, v in data.items():
            matching_key = GRADES_GROUP.fullmatch(k)
            matching_grade = GRADE.fullmatch(k)

            if matching_key:
                _data.update({
                    matching_key.groups()[0]: {
                        'name': data[k],
                        'grades': []
                    }
                })

            elif matching_grade:
                _percentage = 'group_{group}_grade_{grade}_percentage'.format(group=matching_grade.groups()[0],
                                                                              grade=matching_grade.groups()[1])

                if _percentage not in data.keys():
                    raise ValueError

                _data[matching_grade.groups()[0]]['grades'].append((data[k], data[_percentage]))

            else:
                pass

        return _data

    async def can_create_structure(self, school: int) -> Union[bool, int]:
        school_term = await self.school_term(school)

        if school_term:
            return False

        return True

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

    async def school_term(self, school: int):
        query = '''            
            SELECT true
            FROM ciclo_academico
            RIGHT JOIN estructura_notas
                    ON estructura_notas.ciclo_acad_id = ciclo_academico.id
            WHERE ciclo_academico.fecha_comienzo <= $1 AND
                  ciclo_academico.fecha_fin >= $1 AND
                  ciclo_academico.escuela = $2
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(datetime.utcnow() - timedelta(hours=5), school)


routes = {
    'school-term': {
        'create': CreateSchoolTerm,
        'disable-students': DisableStudents,
        'create-grading-structure': CreateGradingStructure
    }
}
