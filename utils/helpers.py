from asyncpg import Record
from aiohttp.web import View
from datetime import datetime
from typing import Union, List, Dict
from aiohttp_jinja2 import template as jinja2_template

from utils.auth import get_auth_data, NotAuthenticated


def view(template: str, *, pass_user: bool = True, encoding: str = 'utf-8', status_code: int = 200):
    def wrapper(func):
        _view_template = template

        if '.' in template:
            _view_template = _view_template.replace('.', '/')

        if template[-5:] != '.html':
            _view_template = _view_template + '.html'

        @jinja2_template(_view_template, encoding=encoding, status=status_code)
        async def _view(_self: View):
            _context = dict()

            if pass_user:
                # We're in a view class
                request = _self.request

                try:
                    user = await get_auth_data(request)
                except NotAuthenticated:
                    user = {}

                _context['user'] = user
                _context.update(await func(_self, user))
            else:
                _context.update(await func(_self))

            return _context

        return _view

    return wrapper


def humanize_datetime(dt: datetime) -> str:
    return str(dt)


def flatten(data: Union[List, Dict, Record]) -> Union[List, Dict]:
    if isinstance(data, (dict, Record)):
        _data = {}

        for k, v in data.items():
            if isinstance(v, datetime):
                _data[k] = humanize_datetime(v)
            elif isinstance(v, (Record, dict, list)):
                _data[k] = flatten(v)
            else:
                _data[k] = v

        return _data
    elif isinstance(data, list):
        _data = []

        for e in data:
            if isinstance(e, datetime):
                _data.append(humanize_datetime(e))
            elif isinstance(e, (Record, dict, list)):
                _data.append(flatten(e))
            else:
                _data.append(e)
    else:
        raise ValueError('Solo se soporta dict y list')

    return _data

