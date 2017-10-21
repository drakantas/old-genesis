from asyncpg import Record
from decimal import Decimal
from typing import Union, List, Dict
from aiohttp_session import get_session
from datetime import datetime
from aiohttp_jinja2 import template as jinja2_template
from aiohttp.web import View, HTTPUnauthorized, HTTPFound

from utils.auth import get_auth_data, NotAuthenticated
from utils.map import parse_data_key


same_year_st = '{year} {month1}-{month2}'
diff_year_str = '{year1} {month1} - {year2} {month2}'


def view(template: str, *, pass_user_: bool = True, encoding: str = 'utf-8', status_code: int = 200):
    def wrapper(func):
        _view_template = template

        if '.' in template:
            _view_template = _view_template.replace('.', '/')

        if template[-5:] != '.html':
            _view_template = _view_template + '.html'

        @jinja2_template(_view_template, encoding=encoding, status=status_code)
        async def _view(_self: View):
            _context = dict()

            if pass_user_:
                # We're in a view class
                request = _self.request

                try:
                    user = await get_auth_data(request)
                except NotAuthenticated:
                    raise

                _context['user'] = flatten(user, {})

                user_permissions = dict(_get_permissions(_context['user']))

                _context['user'] = {k: v for k, v in _context['user'].items() if not k.startswith('perm_')}

                if 'permissions' not in _context['user']:
                    _context['user']['permissions'] = user_permissions

                _context.update(await func(_self, _context['user']))
            else:
                _context.update(await func(_self))

            return _context

        return _view

    return wrapper


def _get_permissions(_user: dict):
    for k in _user.keys():
        if k.startswith('perm_'):
            yield k[5:], _user[k]


def pass_user(func):
    async def _view(_self: View):
        try:
            user = await get_auth_data(_self.request)
        except NotAuthenticated:
            raise

        user = flatten(user, {})

        user_permissions = dict(_get_permissions(user))

        user = {k: v for k, v in user.items() if not k.startswith('perm_')}

        if 'permissions' not in user:
            user['permissions'] = user_permissions

        return await func(_self, user)
    return _view


def logged_out(func):
    async def wrapper(*args, **kwargs):
        if 'id' in await get_session(args[0].request):
            raise HTTPFound('/')

        return await func(*args, **kwargs)
    return wrapper


def permission_required(permission: str):
    def func_container(func):
        async def wrapper(*args):
            user = args[1]

            if permission not in user['permissions']:
                raise PermissionError('El permiso {} no se encontró'.format(permission))

            if user['permissions'][permission]:
                return await func(*args)
            else:
                raise HTTPUnauthorized
        return wrapper
    return func_container


def humanize_datetime(dt: datetime, with_time: bool = True, long: bool = True) -> str:
    args = list(map(lambda x: str(x), (dt.day, parse_data_key(dt.month, 'months'), dt.year)))

    if long:
        datetime_str = '{0} de {1} del {2}'
    else:
        datetime_str = '{0}/{1}/{2}'

    if with_time:
        args.append(dt.strftime("%I:%M %p"))
        datetime_str += ' {3}'

    return datetime_str.format(*args)


def flatten(data: Union[List, Dict, Record], time_config: dict) -> Union[List, Dict]:
    if isinstance(data, (dict, Record)):
        _data = {}

        for k, v in data.items():
            if isinstance(v, datetime):
                _data[k] = humanize_datetime(v, **time_config)
            elif isinstance(v, (Record, dict, list)):
                _data[k] = flatten(v, time_config)
            elif isinstance(v, Decimal):
                _data[k] = float(v)
            else:
                _data[k] = v

        return _data
    elif isinstance(data, list):
        _data = []

        for e in data:
            if isinstance(e, datetime):
                _data.append(humanize_datetime(e, **time_config))
            elif isinstance(e, (Record, dict, list)):
                _data.append(flatten(e, time_config))
            elif isinstance(e, Decimal):
                _data.append(float(e))
            else:
                _data.append(e)
    else:
        raise ValueError('Solo se soporta dict y list')

    return _data


def school_term_to_str(school_term: dict) -> str:
    if school_term['fecha_comienzo'].year == school_term['fecha_fin'].year:
        return same_year_st.format(year=school_term['fecha_comienzo'].year,
                                   month1=parse_data_key(school_term['fecha_comienzo'].month, 'months'),
                                   month2=parse_data_key(school_term['fecha_fin'].month, 'months'))
    return diff_year_str.format(year1=school_term['fecha_comienzo'].year,
                                month1=parse_data_key(school_term['fecha_comienzo'].month, 'months'),
                                year2=school_term['fecha_fin'].year,
                                month2=parse_data_key(school_term['fecha_fin'].month, 'months'))


def check_form_data(data: dict, *args) -> bool:
    if not all([e for e in args if e in data] or [False]):
        return False

    return True


def schedule_to_str(day: int, start_time: int, end_time: int) -> str:
    _day = parse_data_key(day, 'days')

    return '{day} {start_time} - {end_time}'.format(day=_day,
                                                    start_time=_time_to_str(start_time),
                                                    end_time=_time_to_str(end_time))


def _time_to_str(time: int) -> str:
    if time >= 1200 and time != 2400:
        period = 'PM'
    else:
        period = 'AM'

    if period == 'PM':
        _time = time - 1200
    else:
        _time = time

    hours = str(int(_time / 100))
    minutes = _time % 100

    if minutes == 0:
        minutes = '00'
    else:
        minutes = str(minutes)

    if len(hours) == 1:
        hours = '0' + hours

    return '{hours}:{minutes} {period}'.format(hours=hours, minutes=minutes, period=period)


class PermissionNotFound(Exception):
    pass
