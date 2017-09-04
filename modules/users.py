from bcrypt import hashpw, checkpw
from aiohttp.web import View
from aiohttp_jinja2 import template as view

from utils.validator import validator


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
        display_data = {'location': 'registration'}

        data = await self.request.post()
        id_type, id_, password, r_password = data['id_type'], data['id'], data['password'], data['repeat_password']

        errors = await self.validate(id_, password, r_password)

        if not errors:
            id_type, id_ = int(id_type), int(id_)

            try:
                await self.create(id_, id_type, password)
            except:
                raise
            finally:
                display_data['success'] = 'Se ha registrado tus datos. Su cuenta será verificada en las próximas horas.'

        else:
            display_data['errors'] = errors

        return display_data

    @staticmethod
    async def validate(id_: str, password: str, repeat_password: str):
        return validator.validate([
            ['DNI o Carné de extranjería', id_, 'digits|len:9,12'],
            ['Contraseña', password, 'len:8,16'],
            ['Repetir contraseña', repeat_password, 'repeat']
        ])

    async def create(self, id_: int, id_type, password: str):
        query = '''
            INSERT INTO usuario (id, tipo_documento, credencial) VALUES ($1, $2, $3) RETURNING id
        '''

        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(id_, id_type, password)


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
