import re
from typing import Union, Tuple, List
from ryoken.regexes import Regexinator
from inspect import iscoroutinefunction
from asyncpg.pool import PoolConnectionHolder


DIGITS = r'[0-9]+'
LETTERS = r'[a-zA-Z]+'
LENGTH_RULE = r'len:([0-9]+|[0-9]+\,[0-9]+)'
UNIQUE_RULE = r'unique:.+\,.+'
RESTRICTED_VALUE = r'([a-zA-Z0-9_]+)'
COLUMN = RESTRICTED_VALUE + r'(?:<([a-z]+)>)?'
UNIQUE = 'SELECT COUNT(*) FROM {0} WHERE {1}=$1 LIMIT 1'

Cast = {
    'int': int,
    'str': str,
    'dict': dict,
    'list': list,
    'bool': bool
}


class Validator:
    def __init__(self):
        self.digits = re.compile(DIGITS)
        self.letters = re.compile(LETTERS)
        self.length_rule = re.compile(LENGTH_RULE)
        self.unique_rule = re.compile(UNIQUE_RULE)
        self.restricted_value = re.compile(RESTRICTED_VALUE)
        self.column = re.compile(COLUMN)
        self.regexinator = Regexinator()

    async def validate(self, elems: Union[List[Union[List, Tuple]], Tuple[Union[List, Tuple]]],
                       dbi: PoolConnectionHolder = None) -> Union[List[str], bool]:
        """
            validate([
                [$name, $value, $rules, $custom_val_func?],
                ...
            ])
        """
        errors = list()

        for pos, elem in enumerate(elems):
            name, value, rules = elem[0], elem[1], elem[2]
            rules = rules.split('|') if '|' in rules else [rules]

            for rule in rules:
                error = await self._check(value, name, rule, pos, dbi, elems)

                if error:
                    errors.append(error)

                    # Si la verificación de una regla falla, pasar al siguiente elemento
                    break

        return errors or False

    async def _check(self, value: str, name: str, rule: str, pos: int, dbi: PoolConnectionHolder,
                     elems: Union[List[Union[List, Tuple]], Tuple[Union[List, Tuple]]]) -> str:
        if not value:
            return '{} no puede ser dejado en blanco'.format(name)

        if rule in ('digits', 'DIGITS'):
            if not self._only_digits(value):
                return '{} solo puede contener dígitos'.format(name)
        elif rule in ('letters', 'LETTERS'):
            if not self._only_letters(value):
                return '{} solo puede contener letras'.format(name)
        elif rule in ('email', 'EMAIL'):
            if not await self.regexinator.validate(value, strategy='EMAIL'):
                return '{} debe ser de formato john@example.com'.format(name)
        elif rule in ('password', 'PASSWORD'):
            if not await self.regexinator.validate(value, strategy='PASSWORD'):
                return '{} ingresada debe tener 3 caracteres y 3 dígitos por lo menos'.format(name)
        elif self.length_rule.fullmatch(rule):
            len_range = rule[4:]
            len_range = tuple(map(lambda x: int(x), len_range.split(','))) if ',' in len_range else int(len_range)

            if not self._len(value, len_range):
                if isinstance(len_range, tuple):
                    return '{0} debe tener entre {1[0]} y {1[1]} caracteres'.format(name, len_range)
                return '{0} debe tener {1} caracteres'.format(name, len_range)
        elif self.unique_rule.fullmatch(rule):
            column, table = rule[7:].split(',')

            if not (await self._unique(value, table, column, dbi)):
                return 'El {0} ingresado, {1}, ya se encuentra en uso'.format(name, value)
        elif rule in ('repeat', 'REPEAT'):
            if not self._repeated_value(value, pos, elems):
                return 'El valor ingresado en {} no es lo mismo que el ingresado en el ' \
                       'campo {}'.format(name, elems[pos - 1][0])
        elif rule in ('custom', 'CUSTOM'):
            val_func = elems[pos][-1]

            if not (callable(val_func) and iscoroutinefunction(val_func)):
                raise ValueError('Función de validación debe de ser una coroutine')

            try:
                val = await val_func(name, value, pos, elems, dbi)

                if isinstance(val, str):
                    return val
            except TypeError:
                raise TypeError('La función de validación recibe 5 argumentos: name, value, pos, elems, dbi')
        else:
            raise ValueError('Regla de validación no soportada.')

    def _only_digits(self, value: str) -> bool:
        if self.digits.fullmatch(value):
            return True

        return False

    def _only_letters(self, value: str) -> bool:
        if self.letters.fullmatch(value):
            return True

        return False

    @staticmethod
    def _repeated_value(value: str, pos: int, elements: Union[List[Union[List, Tuple]], Tuple[Union[List, Tuple]]]):
        if value == elements[pos - 1][1]:
            return True

        return False

    @staticmethod
    def _len(value: str, range_: Union[Tuple, List, int]) -> bool:
        val_len = len(value)

        if isinstance(range_, int) and val_len >= range_:
            return True

        if range_[0] <= val_len <= range_[1]:
            return True

        return False

    async def _unique(self, value: str, table: str, column: str, dbi: PoolConnectionHolder):
        if not self.restricted_value.fullmatch(table):
            raise ValueError

        _column = self.column.fullmatch(column)

        if not _column:
            raise ValueError

        _type = _column.group(2)

        if _type:
            if _type not in Cast:
                raise ValueError

            value = Cast[_type](value)

        async with dbi.acquire() as connection:
            result = await (await connection.prepare(UNIQUE.format(table, _column.group(1)))).fetchval(value)

            if result > 0:
                return False

        return True


validator = Validator()
