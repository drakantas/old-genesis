from bcrypt import hashpw, checkpw, gensalt
from aiohttp.web import View
from aiohttp_session import get_session
from aiohttp_jinja2 import template as view

from utils.validator import validator


class FailedAuth(Exception):
    pass


class Login(View):
    @view('user/login.html')
    async def get(self) -> dict:
        return {'location': 'login'}

    @view('user/login.html')
    async def post(self) -> dict:
        display_data = {'location': 'login'}

        data = await self.request.post()

        id_, password = data['id'], data['password']

        errors = await self.validate(id_, password)

        if not errors:
            id_ = int(id_)

            try:
                await self.auth(id_, password)
            except FailedAuth as e:
                errors = [str(e)]
            finally:
                await self.init_session(id_)

        if errors:
            display_data['errors'] = errors

        return display_data

    async def init_session(self, id_: int):
        session = await get_session(self.request)
        session['id'] = id_

    @staticmethod
    async def validate(id_: str, password: str):
        return validator.validate([
            ['DNI o Carné de extranjería', id_, 'digits|len:9,12'],
            ['Contraseña', password, 'len:8,16']
        ])

    async def auth(self, id_: int, password: str):
        user = None

        query = '''
            SELECT id, credencial
            FROM usuario
            WHERE id = $1
            LIMIT 1
        '''

        async with self.request.app.db.acquire() as connection:
            user = await (await connection.prepare(query)).fetchrow(id_)

        if not user:
            raise FailedAuth('No existe usuario registrado con el DNI o Carné de extrajería dado')

        if not checkpw(password.encode('utf-8'), user['credencial'].encode('utf-8')):
            raise FailedAuth('Contraseña incorrecta. Intentalo otra vez')


class Registration(View):
    @view('user/new.html')
    async def get(self) -> dict:
        return {'location': 'registration'}

    @view('user/new.html')
    async def post(self) -> dict:
        display_data = {'location': 'registration'}

        data = await self.request.post()
        id_type, id_ = data['id_type'], data['id']
        password, r_password = data['password'], data['repeat_password']
        faculty = data['faculty']

        errors = await self.validate(id_type, id_, password, r_password, faculty)

        if not errors:
            id_type, id_, faculty = int(id_type), int(id_), int(faculty)

            try:
                await self.create(id_, id_type, hashpw(password.encode('utf-8'), gensalt()).decode('utf-8'), faculty)
            except:
                raise
            finally:
                display_data['success'] = 'Se ha registrado tus datos. Su cuenta será verificada en las próximas horas.'

        else:
            display_data['errors'] = errors

        return display_data

    @staticmethod
    async def validate(id_type: str, id_: str, password: str, repeat_password: str, faculty: str):
        return validator.validate([
            ['Tipo de documento', id_type, 'digits|len:1'],
            ['DNI o Carné de extranjería', id_, 'digits|len:9,12'],
            ['Contraseña', password, 'len:8,16'],
            ['Repetir contraseña', repeat_password, 'repeat'],
            ['Facultad', faculty, 'digits|len:1'],
        ])

    async def create(self, id_: int, id_type, password: str, faculty: int):
        query = '''
            INSERT INTO usuario (id, tipo_documento, credencial, facultad) 
            VALUES ($1, $2, $3, $4)
            RETURNING id
        '''

        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(id_, id_type, password, faculty)


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
