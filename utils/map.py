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
    }
}


def parse_data_key(k: int, data_set_: str) -> str:
    if data_set_ not in data_map:
        raise ValueError

    data_set = data_map[data_set_]

    if k not in data_set:
        raise KeyError

    return data_set[k]
