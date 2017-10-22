import asyncio
import bcrypt
from pathlib import Path
from ryoken.json import JSON
from datetime import datetime
from asyncpg.pool import PoolConnectionHolder
from asyncpg import create_pool

from config import db_dsn

students_data = './_setup/students.json'
students_data = Path(students_data)

roles_data = './_setup/roles.json'
roles_data = Path(roles_data)


async def get_data(path: Path) -> list:
    with open(str(path), 'rb') as f:
        return await JSON.decode(f.read().decode('utf-8'))


def parse_data(data: list):
    now = datetime.utcnow()
    for s in data:
        yield {**s,
               'tipo_documento': 0,
               'correo_electronico': s['nombres'].replace(' ', '_').lower() + '@usmp.pe',
               'credencial': bcrypt.hashpw(s['nombres'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
               'escuela': 1,
               'rol_id': 1,
               'fecha_creacion': now,
               'fecha_ultima_actualizacion': now,
               'autorizado': True,
               'deshabilitado': False}


async def do_transaction(data: list, table: str, returning: str, dbi: PoolConnectionHolder) -> str:
    columns = data[0].keys()
    values = list()

    for u in data:
        _u = []
        for c in columns:
            _u.append(str(u[c]))
        _u = '(\'' + '\', \''.join(_u) + '\')'
        values.append(_u)

    if values:
        values = ', '.join(values)

    query = '''
        INSERT INTO {table} {columns}
        VALUES {values}
        RETURNING {returning};
    '''.format(table=table, columns='("' + '", "'.join(columns) + '")', values=values, returning=returning)

    async with dbi.acquire() as connection:
        async with connection.transaction():
            return await connection.fetch(query)


def main():
    loop = asyncio.get_event_loop()
    _students_data = loop.run_until_complete(get_data(students_data))
    _students_data = list(parse_data(_students_data))

    _roles_data = list(loop.run_until_complete(get_data(roles_data)))

    pool = loop.run_until_complete(create_pool(dsn=db_dsn))

    school_term = loop.run_until_complete(do_transaction([{
        'escuela': 1,
        'fecha_comienzo': '2017-10-01 00:00:00',
        'fecha_fin': '2017-10-31 23:59:00'
    }], 'ciclo_academico', 'id', pool))

    roles = loop.run_until_complete(do_transaction(_roles_data, 'rol_usuario', 'id', pool))
    students = loop.run_until_complete(do_transaction(_students_data, 'usuario', 'id', pool))

    def map_registration(student: dict) -> dict:
        return {
            'estudiante_id': student['id'],
            'ciclo_acad_id': school_term[0]['id']
        }

    registrations = loop.run_until_complete(do_transaction(list(map(map_registration, students)),
                                                           'matricula', 'estudiante_id, ciclo_acad_id', pool))

    print(list(registrations))


if __name__ == '__main__':
    main()
