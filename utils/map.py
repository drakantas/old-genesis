from typing import Generator, Union

data_map = {
    'id_types': {
        0: 'DNI',
        1: 'Carné de extranjería'
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
    }
}


def parse_data_key(k: Union[int, str], data_set_: str) -> str:
    if data_set_ not in data_map:
        raise ValueError

    data_set = data_map[data_set_]

    if k not in data_set:
        raise KeyError

    return data_set[k]


def map_users(users: Generator) -> list:
    def _convert_data_keys(user: dict) -> dict:
        user['escuela'] = parse_data_key(user['escuela'], 'schools')
        user['tipo_documento'] = parse_data_key(user['tipo_documento'], 'id_types')
        return user
    return list(map(_convert_data_keys, [dict(user) for user in users]))
