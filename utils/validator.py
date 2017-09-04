import re
from typing import Union, Tuple, List

DIGITS = r'[0-9]+'
LETTERS = r'[a-zA-Z]+'
LENGTH_RULE = r'len:([0-9]+|[0-9]+\,[0-9]+)'


class Validator:
    def __init__(self):
        self.digits = re.compile(DIGITS)
        self.letters = re.compile(LETTERS)
        self.length_rule = re.compile(LENGTH_RULE)

    def validate(self, elems: Union[List[Union[List, Tuple]], Tuple[Union[List, Tuple]]]):
        """
            validate([
                [$name, $value, $rules],
                ...
            ])
        """
        errors = list()

        def check_single_value(value_: str, name_: str, rule_: str, pos_: int, errors_: List = errors,
                               elems_: Union[List[Union[List, Tuple]], Tuple[Union[List, Tuple]]] = elems):
            if rule_ in ('digits', 'DIGITS'):
                if not self._only_digits(value_):
                    errors_.append('{} solo puede contener dígitos'.format(name_))
            elif rule_ in ('letters', 'LETTERS'):
                if not self._only_letters(value_):
                    errors_.append('{} solo puede contener letras'.format(name_))
            elif self.length_rule.fullmatch(rule_):
                len_range = rule_[4:]
                len_range = tuple(map(lambda x: int(x), len_range.split(','))) if ',' in len_range else int(len_range)

                if not self._len(value_, len_range):
                    errors_.append('{0} no se encuentra en el rango de {1}'.format(name_, rule_[4:]))
            elif rule_ in ('repeat', 'REPEAT'):
                if not self._repeated_value(value_, pos_, elems_):
                    errors_.append('El valor ingresado en {} no es lo mismo que el ingresado '
                                   'en el campo {}'.format(name_, elems_[pos_ - 1][0]))
            else:
                raise ValueError('Regla de validación no soportada.')

        for pos, elem in enumerate(elems):
            name, value, rules = elem
            rules = rules.split('|') if '|' in rules else [rules]

            for rule in rules:
                check_single_value(value, name, rule, pos)

        return errors if errors else False

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


validator = Validator()
