from aiohttp.web import View
from aiohttp_jinja2 import template as view


class Login(View):
    @view('user/login.html')
    async def get(self) -> dict:
        return {'location': 'login'}

    @view('user/login.html')
    async def post(self) -> dict:
        return {'location': 'login'}


class Registration(View):
    @view('user/new.html')
    async def get(self) -> dict:
        return {'location': 'registration'}

    @view('user/new.html')
    async def post(self) -> dict:
        return {'location': 'registration'}


class RecoverPassword(View):
    @view('user/recover_password.html')
    async def get(self) -> dict:
        return {'location': 'recover_password'}

    @view('user/recover_password.html')
    async def post(self) -> dict:
        return {'location': 'recover_password'}

routes = {
    "login": Login,
    "register": Registration,
    "recover-password": RecoverPassword
}
