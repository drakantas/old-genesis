import re
from aiohttp.web import View
from datetime import datetime
from typing import Union
from asyncpg.pool import PoolConnectionHolder

from utils.helpers import view, humanize_datetime
from utils.map import map_users
from utils.validator import validator


# Muy malo...
MM_DD_YYYY_FORMAT = r'(?:0[1-9]|10|11|12)\/[0-3][0-9]\/20[0-9]{2}'
MM_DD_YYYY = re.compile(MM_DD_YYYY_FORMAT)
SCHEDULE_KEY_FORMAT = r'schedule_([0-9]+)_(?:teacher|day|start_time|end_time)'
SCHEDULE_KEY = re.compile(SCHEDULE_KEY_FORMAT)
TIME_FORMAT = r'(?:1|2|3|4|5|6|7|8|9|10|11|12):[0-5][0-9] (?:AM|PM)'
TIME = re.compile(TIME_FORMAT)

df = '%m/%d/%Y'


class CreateSchoolTerm(View):
    @view('school_term.create')
    async def get(self, user: dict):
        teachers = map_users(await self.fetch_teachers(user['escuela'], 2, self.request.app.db))

        return {'teachers': teachers,
                'today': humanize_datetime(datetime.utcnow(), with_time=False)}

    @view('school_term.create')
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

            if await self.fetch_school_term(start_date, self.request.app.db):
                _e.append('La fecha de comienzo ya se encuentra en el rango que abarca otro ciclo académico')

            if await self.fetch_school_term(end_date, self.request.app.db):
                _e.append('La fecha de culminación ya se encuentra en el rango que abarca otro ciclo académico')

            if _e:
                result_data['errors'] = _e
            else:
                validation_groups = await self._get_validation_groups(data)
                validation_rules = await self._build_validation_groups(validation_groups, data)

                _validation_errors = await validator.validate(validation_rules, self.request.app.db)

                if _validation_errors:
                    result_data['errors'] = _validation_errors
                else:
                    await self.create(validation_groups, data, self.request.app.db)
                    result_data['success'] = 'Se ha creado el ciclo académico exitosamente.'

            del _e

        return result_data

    async def validate(self, data: dict):
        return await validator.validate([
            ['Fecha comienzo', data['beginning_date'], 'len:10|custom', self._validate_date],
            ['Fecha de culminación', data['ending_date'], 'len:10|custom', self._validate_date]
        ], self.request.app.db)

    async def create(self, groups: list, data: dict, dbi: PoolConnectionHolder):
        query = '''
            WITH ciclo_acad AS (
                INSERT INTO ciclo_academico (fecha_comienzo, fecha_fin)
                VALUES ($1, $2)
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
                await connection.execute(query, datetime.strptime(data['beginning_date'], df), datetime.strptime(data['ending_date'], df))

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
    async def fetch_school_term(date: datetime, dbi: PoolConnectionHolder):
        query = '''
            SELECT id
            FROM ciclo_academico
            WHERE $1 >= fecha_comienzo AND
                  $1 <= fecha_fin
            LIMIT 1
        '''
        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(date)


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