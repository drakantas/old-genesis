from typing import Generator, Union, List

data_map = {
    'id_types': {
        0: 'DNI',
        1: 'Carné de extranjería'
    },

    'sexes': {
        0: 'Masculino',
        1: 'Femenino'
    },

    'schools': {
        1: 'Computación y sistemas',
        2: 'Industrial',
        3: 'Civil',
        4: 'Arquitectura',
        5: 'Electrónica',
        6: 'Derecho',
        7: 'Medicina',
        8: 'Aeronáutica'
    },

    'files': {
        'doc': 'application/msword',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'pdf': 'application/pdf'
    },

    'months': {
        1: 'Enero',
        2: 'Febrero',
        3: 'Marzo',
        4: 'Abríl',
        5: 'Mayo',
        6: 'Junio',
        7: 'Julio',
        8: 'Agosto',
        9: 'Septiembre',
        10: 'Octubre',
        11: 'Noviembre',
        12: 'Diciembre'
    }
}


def parse_data_key(k: Union[int, str], data_set_: str) -> str:
    if data_set_ not in data_map:
        raise ValueError

    data_set = data_map[data_set_]

    if k not in data_set:
        raise KeyError

    return data_set[k]


def map_users(users: Union[Generator, List]) -> list:
    def _convert_data_keys(user: dict) -> dict:
        if 'escuela' in user:
            user['escuela'] = parse_data_key(user['escuela'], 'schools')
        if 'tipo_documento' in user:
            user['tipo_documento'] = parse_data_key(user['tipo_documento'], 'id_types')
        if 'sexo' in user:
            user['sexo'] = parse_data_key(user['sexo'] or 0, 'sexes')
        return user
    return list(map(_convert_data_keys, [dict(user) for user in users]))
