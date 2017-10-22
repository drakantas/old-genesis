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
    },

    'days': {
        0: 'Domingo',
        1: 'Lunes',
        2: 'Martes',
        3: 'Miércoles',
        4: 'Jueves',
        5: 'Viernes',
        6: 'Sábado'
    },

    'isoweekdays': {
        0: 6,  # Domingo
        1: 0,  # Lunes
        2: 1,
        3: 2,
        4: 3,
        5: 4,
        6: 5   # Sábado
    },

    'disabled': {
        0: 'Habilitado',
        1: 'Deshabilitado'
    },

    'authorized': {
        0: 'No autorizado',
        1: 'Autorizado'
    },

    'districts': {
        0: 'Cieneguilla',
        1: 'Comas',
        2: 'El Agustino',
        3: 'Independencia',
        4: 'Jesús María',
        5: 'La Molina',
        6: 'La Victoria',
        7: 'Lima',
        8: 'Lince',
        9: 'Los Olivos',
        10: 'Lurigancho-Chosica',
        11: 'Lurin',
        12: 'Magdalena del Mar',
        13: 'Miraflores',
        14: 'Pueblo Libre',
        15: 'Pachacámac',
        16: 'Pucusana',
        17: 'Puente Piedra',
        18: 'Punta Hermosa',
        19: 'Punta Negra',
        20: 'Rímac',
        21: 'San Bartolo',
        22: 'San Borja',
        23: 'San Isidro',
        24: 'San Juan de Lurigancho',
        25: 'San Juan de Miraflores',
        26: 'San Luis',
        27: 'San Martín de Porres',
        28: 'San Miguel',
        29: 'Santa Anita',
        30: 'Santa María del Mar',
        31: 'Santa Rosa',
        32: 'Santiago de Surco',
        33: 'Surquillo',
        34: 'Villa El Salvador',
        35: 'Villa María del Triunfo',
        36: 'Callao (Cercado)',
        37: 'Bellavista',
        38: 'Carmen de La Legua-Reynoso',
        39: 'La Perla',
        40: 'La Punta',
        41: 'Ventanilla',
        42: 'Mi Perú',
    },

    'nationalities': {
        'AL': 'Albania',
        'AR': 'Argentina',
        'AM': 'Armenia',
        'AU': 'Australia',
        'AT': 'Austria',
        'BY': 'Bielorrusia',
        'BE': 'Bélgica',
        'BO': 'Bolivia',
        'BA': 'Bosnia y Herzegovina',
        'BR': 'Brasil',
        'BG': 'Bulgaria',
        'CA': 'Canadá',
        'CL': 'Chile',
        'CN': 'China',
        'CO': 'Colombia',
        'HR': 'Croacia',
        'CU': 'Cuba',
        'CY': 'Chipre',
        'CZ': 'República Checa',
        'DK': 'Dinamarca',
        'EG': 'Egipto',
        'EE': 'Estonia',
        'FI': 'Finlandia',
        'FR': 'Francia',
        'GE': 'Georgia',
        'DE': 'Alemania',
        'GR': 'Grecia',
        'HU': 'Hungría',
        'IN': 'India',
        'ID': 'Indonesia',
        'IR': 'Irán',
        'IE': 'Irlanda',
        'IL': 'Israel',
        'IT': 'Italia',
        'JP': 'Japón',
        'LV': 'Letonia',
        'LT': 'Lituania',
        'MY': 'Malasia',
        'MX': 'México',
        'ME': 'Montenegro',
        'NL': 'Países Bajos',
        'NZ': 'Nueva Zelanda',
        'NG': 'Nigeria',
        'KP': 'Corea del Norte',
        'NO': 'Noruega',
        'PK': 'Pakistán',
        'PY': 'Paraguay',
        'PE': 'Perú',
        'PH': 'Filipinas',
        'PL': 'Polonia',
        'PT': 'Portugal',
        'TW': 'Taiwán',
        'MK': 'ARY Macedonia',
        'MD': 'Moldavia',
        'RO': 'Rumania',
        'RU': 'Rusia',
        'SA': 'Arabia Saudita',
        'RS': 'Serbia',
        'SG': 'Singapur',
        'SK': 'Eslovaquia',
        'SI': 'Eslovenia',
        'ZA': 'Sudáfrica',
        'KR': 'Corea del Sur',
        'ES': 'España',
        'SE': 'Suecia',
        'CH': 'Suiza',
        'TH': 'Tailandia',
        'TR': 'Turquía',
        'UA': 'Ucrania',
        'AE': 'Emiratos Árabes Unidos',
        'GB': 'Reino Unido',
        'UY': 'Uruguay',
        'US': 'Estados Unidos',
        'VE': 'Venezuela'
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

        if 'distrito' in user:
            user['distrito'] = parse_data_key(user['distrito'] or 0, 'districts')

        if 'nacionalidad' in user:
            user['nacionalidad'] = parse_data_key(user['nacionalidad'] or 'PE', 'nationalities')

        return user
    return list(map(_convert_data_keys, [dict(user) for user in users]))
