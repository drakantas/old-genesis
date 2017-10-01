from aiohttp.web import View
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
