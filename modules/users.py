from typing import Union
from base64 import b64encode
from datetime import datetime
from aiohttp_session import get_session
from bcrypt import hashpw, checkpw, gensalt
from aiohttp_jinja2 import template
from aiohttp.web import View, web_request, HTTPFound

from utils.map import map_users
from utils.helpers import pass_user, view
from utils.validator import validator


class FailedAuth(Exception):
    pass


class Login(View):
    @template('user/login.html')
    async def get(self) -> dict:
        return {'location': 'login'}

    @template('user/login.html')
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
        return await validator.validate([
            ['DNI o Carné de extranjería', id_, 'digits|len:9,12'],
            ['Contraseña', password, 'len:8,16']
        ])

    async def auth(self, id_: int, password: str):
        user = None

        query = '''
            SELECT id, credencial, autorizado, deshabilitado
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

        if user['deshabilitado']:
            raise FailedAuth('Tu cuenta se encuentra deshabilitada')

        if not user['autorizado']:
            raise FailedAuth('Aún no se ha autorizado tu cuenta')


class Registration(View):
    @template('user/new.html')
    async def get(self) -> dict:
        return {'location': 'registration'}

    @template('user/new.html')
    async def post(self) -> dict:
        display_data = {'location': 'registration'}

        data = await self.request.post()

        name, last_name, email = data['name'], data['last_name'], data['email']
        id_type, id_ = data['id_type'], data['id']
        password, r_password = data['password'], data['repeat_password']
        school = data['school']
        attached_doc = data['attach_doc']

        errors = await self.validate(id_type, id_, name, last_name, email, password, r_password, school, attached_doc)

        if not errors:
            id_type, id_, faculty = int(id_type), int(id_), int(school)

            try:
                await self.create(id_, id_type, hashpw(password.encode('utf-8'), gensalt()).decode('utf-8'),
                                  name, last_name, email, faculty,
                                  [*attached_doc.filename.rsplit('.', maxsplit=1), attached_doc.file.read()])
            except:
                raise
            finally:
                display_data['success'] = 'Se ha registrado tus datos. Su cuenta será verificada en las próximas horas.'

        else:
            display_data['errors'] = errors

        return display_data

    async def validate(self, id_type: str, id_: str, name: str, last_name: str, email: str, password: str,
                       repeat_password: str, school: str, attached_doc: Union[bytearray, web_request.FileField]):
        return await validator.validate([
            ['Nombres', name, 'len:8,64'],
            ['Apellidos', last_name, 'len:8,84'],
            ['Correo electrónico', email, 'len:14,128|email|unique:correo_electronico,usuario'],
            ['Tipo de documento', id_type, 'digits|len:1|custom', self.validate_document_type],
            ['DNI o Carné de extranjería', id_, 'digits|custom|unique:id<int>,usuario', self.validate_id],
            ['Contraseña', password, 'len:8,16|password'],
            ['Repetir contraseña', repeat_password, 'repeat'],
            ['Escuela', school, 'digits|len:1'],
            ['Documento adjunto', attached_doc, 'custom', self.validate_attached_doc]
        ], self.request.app.db)

    @staticmethod
    async def validate_attached_doc(name: str, value: web_request.FileField, *args):
        if not isinstance(value, web_request.FileField):
            return 'Algo ha sucedido, no se pudo validar el archivo'

        if value.content_type not in ('application/msword',
                                      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                      'application/pdf'):
            return 'Tipo de archivo no soportado, solo PDFs o DOCs'

        # Se debe de separar la subida de archivos a otro formulario de tipo multipart con el cual manejar la subida
        # como un stream y detenerlo si excede los 10MBs, esto de aquí es muy propenso a error
        # TODO

    @staticmethod
    async def validate_document_type(name: str, value: str, *args):
        if value not in ('0', '1'):
            return '{} debe de ser 0 ó 1'.format(name)

    @staticmethod
    async def validate_id(name: str, value: str, pos: int, elems: list, dbi):
        id_type, len_val = int(elems[pos - 1][1]), len(value)

        if id_type == 0:
            if len_val != 9:
                return 'El DNI debe contener 9 caracteres'
        elif id_type == 1:
            if len_val != 12:
                return 'El Carné de extranjería debe contener 12 caracteres'
        else:
            return 'Ingrese un tipo de documento correcto'

    async def create(self, id_: int, id_type: int, password: str, name: str, last_name: str, email: str, school: int,
                     attached_doc: list):
        query = '''
            WITH estudiante AS (
                INSERT INTO usuario (id, tipo_documento, credencial, nombres,
                                     apellidos, correo_electronico, escuela, autorizado,
                                     deshabilitado, fecha_creacion, fecha_ultima_actualizacion,
                                     rol_id) 
                VALUES ($1, $2, $3, $4, $5, $6, $7, false, false, $8, $9, $15)
                RETURNING id
            ), archivo AS (
                INSERT INTO archivo (nombre, ext, contenido, fecha_subido)
                VALUES ($10, $11, $12, $13)
                RETURNING id
            )
            INSERT INTO solicitud_autorizacion (alumno_id, fecha_creacion, archivo_id)
            VALUES (
                (SELECT id FROM estudiante LIMIT 1),
                $14,
                (SELECT id FROM archivo LIMIT 1)
            )
        '''
        now = datetime.utcnow()
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(id_, id_type, password, name,
                                                                 last_name, email, school, now,
                                                                 now, attached_doc[0], attached_doc[1], attached_doc[2],
                                                                 now, now, 1)


class RecoverPassword(View):
    @template('user/recover_password.html')
    async def get(self) -> dict:
        return {'location': 'recover_password'}

    @template('user/recover_password.html')
    async def post(self) -> dict:

        return {'location': 'recover_password'}


class Logout(View):
    async def get(self):
        return await self.logout()

    async def post(self):
        return await self.logout()

    async def logout(self):
        session = await get_session(self.request)

        if 'id' in session:
            del session['id']

        return HTTPFound('/login')


class UpdateAvatar(View):
    @pass_user
    async def get(self, user: dict):
        return HTTPFound('/settings/edit-profile')

    @view('user.edit_profile')
    async def post(self, user: dict):
        reader = await self.request.multipart()

        avatar = await reader.next()

        if avatar is None:
            return {'errors': ['Data enviada no es correcta...']}

        if avatar.headers['Content-Type'] not in ('image/png', 'image/jpeg'):
            return {'errors': ['Solo se soporta los formatos jpeg y png']}

        size = 0
        size_error = False
        _avatar = None

        while True:
            chunk = await avatar.read_chunk()

            if not chunk:
                break

            if _avatar is None:
                _avatar = chunk
            else:
                _avatar = _avatar + chunk

            size += len(chunk)

            if size >= 2 * 1024 * 1024:  # 5 MiB
                del _avatar
                size_error = True
                break

        if size_error:
            return {'errors': ['El avatar no puede pesar más de 2MBs']}

        await self.update(user['id'], bytearray(b64encode(_avatar)))

        return {'success': 'Se ha actualizado tu avatar'}

    async def update(self, id_: int, chunk: bytearray):
        query = '''
            UPDATE usuario
            SET avatar = $2
            WHERE id = $1
        '''
        async with self.request.app.db.acquire() as connection:
            return await connection.execute(query, id_, chunk)


class UsersList(View):
    @view('user.list')
    async def get(self, user: dict):
        if 'page' in self.request.match_info:
            page = int(self.request.match_info['page'])
        else:
            page = 1

        offset = (page - 1) * 20
        users = await self.fetch_users(user['escuela'], offset)
        users = map_users(users)

        return {'users': users}

    async def fetch_users(self, school: int, offset: int):
        query = '''
            SELECT usuario.id, tipo_documento, nombres, apellidos, rol_usuario.desc as rol, sexo, deshabilitado, autorizado, escuela
            FROM usuario
            LEFT JOIN rol_usuario
                   ON rol_usuario.id = usuario.rol_id
            WHERE usuario.escuela = $1
            ORDER BY rol_usuario.desc ASC
            LIMIT 20 OFFSET $2
        '''

        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school, offset)


routes = {
    'login': Login,
    'logout': Logout,
    'register': Registration,
    'recover-password': RecoverPassword,
    'settings': {
        'update-avatar': UpdateAvatar
    },
    'users/list':  UsersList,
    'users/list/page-{page:[1-9][0-9]*}': UsersList
}
