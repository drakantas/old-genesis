from base64 import b64encode
from aiohttp_jinja2 import template
from aiohttp_session import get_session
from datetime import datetime, timedelta
from bcrypt import hashpw, checkpw, gensalt
from asyncpg.pool import PoolConnectionHolder
from aiohttp.web import View, web_request, HTTPFound, HTTPNotFound

from utils.validator import validator
from utils.map import map_users, parse_data_key, data_map
from utils.helpers import pass_user, view, logged_out, check_form_data, pagination, permission_required, flatten


class FailedAuth(Exception):
    pass


class Login(View):
    @logged_out
    @template('user/login.html')
    async def get(self) -> dict:
        return {'location': 'login'}

    @logged_out
    @template('user/login.html')
    async def post(self) -> dict:
        display_data = {'location': 'login'}

        data = await self.request.post()

        if not check_form_data(data, 'id', 'password'):
            display_data.update({'error': 'No se ha enviado los parámetros necesarios...'})
            return display_data

        id_, password = data['id'], data['password']

        errors = await self.validate(id_, password)

        if not errors:
            id_ = int(id_)

            try:
                await self.auth(id_, password);
            except FailedAuth as e:
                display_data.update({'error': str(e)});
            else:
                await self.init_session(id_);

                raise HTTPFound('/')  # Redirigir al landing page
        else:
            display_data.update({'errors': errors})

        return display_data

    async def init_session(self, id_: int):
        session = await get_session(self.request)
        session['id'] = id_

    @staticmethod
    async def validate(id_: str, password: str):
        return await validator.validate([
            ['DNI o Carné de extranjería', id_, 'digits|len:8,12'],
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
    @logged_out
    @template('user/new.html')
    async def get(self) -> dict:
        display_data = {'location': 'registration'}

        session = await get_session(self.request)

        if 'app' in session:
            display_data.update({'file': session['app']['filename']})

        return display_data

    @logged_out
    @template('user/new.html')
    async def post(self) -> dict:
        display_data = {'location': 'registration'}

        session = await get_session(self.request)

        if 'app' not in session:
            display_data.update({'error': 'Debes de primero subir el archivo.'})
            return display_data

        display_data.update({'file': session['app']['filename']})
        file_id = session['app']['id']

        data = await self.request.post()

        if not check_form_data(data, 'name', 'last_name', 'email', 'id_type', 'id', 'school', 'password',
                               'repeat_password'):
            display_data.update({'error': 'No se enviaron los parámetros necesarios...'})
            return display_data

        errors = await self.validate(data)

        if errors:
            display_data.update({'errors': errors, 'data': data})
            return display_data

        await self.create(int(data['id']), int(data['id_type']),
                          hashpw(data['password'].encode('utf-8'), gensalt()).decode('utf-8'),
                          data['name'], data['last_name'], data['email'], int(data['school']),
                          file_id)

        del session['app']

        display_data.update({'success': 'Se ha registrado al usuario exitosamente. Sin embargo, deberás de esperar'
                                        'a que se autorice tu cuenta antes de que puedas acceder al sistema.'})
        return display_data

    async def validate(self, data: dict):
        return await validator.validate([
            ['Nombres', data['name'], 'len:4,64'],
            ['Apellidos', data['last_name'], 'len:4,84'],
            ['Correo electrónico', data['email'], 'len:14,128|email|unique:correo_electronico,usuario'],
            ['Tipo de documento', data['id_type'], 'digits|len:1|custom', self._validate_document_type],
            ['DNI o Carné de extranjería', data['id'], 'digits|custom|unique:id<int>,usuario', self._validate_id],
            ['Contraseña', data['password'], 'len:8,16|password'],
            ['Repetir contraseña', data['repeat_password'], 'repeat'],
            ['Escuela', data['school'], 'digits|len:1|custom', self._validate_school]
        ], self.request.app.db)

    @staticmethod
    async def _validate_school(name: str, value: str, *args):
        try:
            parse_data_key(int(value), 'schools')
        except KeyError:
            return 'La escuela ingresada es incorrecta...'

    @staticmethod
    async def _validate_document_type(name: str, value: str, *args):
        if value not in ('0', '1'):
            return '{} debe de ser 0 ó 1'.format(name)

    @staticmethod
    async def _validate_id(name: str, value: str, pos: int, elems: list, dbi):
        id_type, len_val = int(elems[pos - 1][1]), len(value)

        if id_type == 0:
            if not(8 <= len_val < 10):
                return 'El DNI debe contener 8 o 9 caracteres'
        elif id_type == 1:
            if len_val != 12:
                return 'El Carné de extranjería debe contener 12 caracteres'
        else:
            return 'Ingrese un tipo de documento correcto'

    async def create(self, id_: int, id_type: int, password: str, name: str, last_name: str, email: str, school: int,
                     file_id: int):
        query = '''
            WITH estudiante AS (
                INSERT INTO usuario (id, tipo_documento, credencial, nombres,
                                     apellidos, correo_electronico, escuela, autorizado,
                                     deshabilitado, fecha_creacion, fecha_ultima_actualizacion,
                                     rol_id) 
                VALUES ($1, $2, $3, $4, $5, $6, $7, false, false, $8, $8, 1)
                RETURNING id
            )
            INSERT INTO solicitud_autorizacion (alumno_id, fecha_creacion, archivo_id)
            VALUES ((SELECT id FROM estudiante), $8, $9)
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(id_, id_type, password, name, last_name, email, school,
                                                                 datetime.utcnow() - timedelta(hours=5),
                                                                 file_id)


class UploadApplication(View):
    @logged_out
    @template('user/new.html')
    async def post(self):
        display_data = {'location': 'registration'}

        reader = await self.request.multipart()

        file = await reader.next()

        if file is None:
            display_data.update({'error': 'No se envió el parámetro necesario...'})
            return display_data

        if file.headers['Content-Type'] not in data_map['files'].values():
            display_data.update({'error': 'El archivo debe de ser un PDF o Windows Office Doc.'})
            return display_data

        file_size = 0
        _file = None
        size_error = False

        while True:
            chunk = await file.read_chunk()

            if not chunk:
                break

            if _file is None:
                _file = chunk
            else:
                _file = _file + chunk

            file_size += len(chunk)

            if file_size > 3 * 1024 * 1024:
                size_error = True
                break

        if size_error:
            del _file, file_size
            display_data.update({'error': 'El archivo no puede pesar más de 3MBs.'})
            return display_data

        file_id = await self.create(file.filename.rsplit('.', 1), _file)

        session = await get_session(self.request)

        session['app'] = {'id': file_id, 'filename': file.filename}

        raise HTTPFound('/register')

    async def create(self, file_details: list, file: bytearray):
        statement = '''
            INSERT INTO archivo (nombre, ext, contenido, fecha_subido)
            VALUES ($1, $2, $3, $4)
            RETURNING id
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(statement)).fetchval(*file_details, file,
                                                                        datetime.utcnow() - timedelta(hours=5))


class RecoverPassword(View):
    @logged_out
    @template('user/recover_password.html')
    async def get(self):
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
            return {'errors': ['Data enviada no es correcta...'],
                    'districts': data_map['districts'],
                    'nationalities': data_map['nationalities']}

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

            if size > 2 * 1024 * 1024:  # 5 MiB
                del _avatar
                size_error = True
                break

        if size_error:
            return {'errors': ['El avatar no puede pesar más de 2MBs'],
                    'districts': data_map['districts'],
                    'nationalities': data_map['nationalities']}

        await self.update(user['id'], bytearray(b64encode(_avatar)))

        return {'success': 'Se ha actualizado tu avatar',
                'districts': data_map['districts'],
                'nationalities': data_map['nationalities']}

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
    @permission_required('mantener_usuarios')
    async def get(self, user: dict):
        if 'page' in self.request.match_info:
            page = int(self.request.match_info['page'])
        else:
            page = 1

        offset = (page - 1) * 20
        users = await self.fetch_users(user['escuela'], offset)
        users = map_users(users)

        if not users:
            raise HTTPNotFound

        users_amount = await self.get_users_amount(user['escuela'])

        return {'users': users,
                'page': page,
                'users_amount': users_amount,
                'pagination': pagination(page, users_amount)}

    async def fetch_users(self, school: int, offset: int):
        query = '''
            SELECT usuario.id, tipo_documento, nombres, apellidos, rol_usuario.desc as rol, sexo, deshabilitado,
                   autorizado, escuela
            FROM usuario
            LEFT JOIN rol_usuario
                   ON rol_usuario.id = usuario.rol_id
            WHERE usuario.escuela = $1
            ORDER BY rol_usuario.id DESC, usuario.deshabilitado ASC
            LIMIT 20 OFFSET $2
        '''

        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school, offset)

    async def get_users_amount(self, school: int):
        query = '''
            SELECT COUNT(true)
            FROM usuario
            WHERE usuario.escuela = $1
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school)


class ChangePassword(View):
    @view('user.change_password')
    async def get(self, user: dict):
        return {}

    @view('user.change_password')
    async def post(self, user: dict):
        data = await self.request.post()

        if not('current_password' in data and 'new_password' in data and 'repeat_new_password' in data):
            return {'errors': ['Data enviada no es correcta...']}

        errors = await self.validate(data, user['id'])

        if errors:
            return {'errors': errors}

        await self.update(user['id'], hashpw(data['new_password'].encode('utf-8'), gensalt()))

        return {'success': 'Se ha cambiado tu contraseña exitosamente'}

    async def validate(self, data: dict, user: int):
        return await validator.validate([
            ['Contraseña actual', data['current_password'], 'len:8,16|password|custom', self._validate_password, user],
            ['Nueva contraseña', data['new_password'], 'len:8,16|password'],
            ['Repetir nueva contraseña', data['repeat_new_password'], 'repeat']
        ], self.request.app.db)

    async def update(self, user: int, new_password: bytes):
        async with self.request.app.db.acquire() as connection:
            await connection.execute('''
                UPDATE usuario SET credencial = $2 WHERE id = $1
            ''', user, new_password.decode('utf-8'))

    @staticmethod
    async def _validate_password(name: str, value: str, pos: int, elems: list, dbi: PoolConnectionHolder,
                                 user: int):
        async with dbi.acquire() as connection:
            current_password = (await (
                await connection.prepare('SELECT credencial FROM usuario WHERE id = $1 LIMIT 1')
            ).fetchval(user)).encode('utf-8')

        if not checkpw(value.encode('utf-8'), current_password):
            return '{} ingresada incorrecta'.format(name)


class ReadProfile(View):
    @view('user.view_profile')
    async def get(self, user: dict):
        if '_user_id' not in self.request.match_info:
            raise HTTPNotFound  # No se pasó una id de usuario por la URI, 404

        # Obtenemos la ID de usuario
        _user_id = int(self.request.match_info['_user_id'])

        _user = await self.get_user(_user_id)  # Consultar la BD por usuario

        if not _user:
            raise HTTPNotFound  # No se encontró al usuario, 404

        return {'requested_user': map_users([_user])[0]}

    async def get_user(self, user_id: int):
        query = '''
            SELECT id, tipo_documento, nombres, apellidos,
                   direccion, correo_electronico, nro_telefono, nacionalidad,
                   escuela, distrito, sexo, avatar
            FROM usuario
            WHERE id = $1
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(user_id)


class EditProfile(View):
    @view('user.edit_profile')
    async def get(self, user: dict):
        return {'districts': data_map['districts'],
                'nationalities': data_map['nationalities']}

    @view('user.edit_profile')
    async def post(self, user: dict):
        display_data = {'districts': data_map['districts'],
                        'nationalities': data_map['nationalities']}

        student_id = user['id']

        data = dict(await self.request.post())

        if not all(['name' in data, 'last_name' in data, 'address' in data,
                    'email' in data, 'phone' in data, 'nationality' in data,
                    'district' in data, 'gender' in data]):
            return {'errors': ['La data enviada no es la esperada...']}

        errors = await self.validate(data, user['id'])

        if not errors:

            await self.update(student_id, data['name'], data['last_name'],
                              data['address'], data['email'], int(data['phone']),
                              data['nationality'], int(data['district']), int(data['gender']))

            display_data['success'] = 'Se han registrado los cambios. Se han actualizado tus datos.'

        else:
            display_data['errors'] = errors

        return display_data

    async def validate(self, data: dict, user_id: int):
        return await validator.validate([
            ['Nombres', data['name'], 'len:8,64'],
            ['Apellidos', data['last_name'], 'len:8,64'],
            ['Dirección', data['address'], 'len:8,64'],
            ['Email', data['email'], 'len:14,128|email|custom', self._validate_email, user_id],
            ['Teléfono', data['phone'], 'digits|len:9'],
            ['Nacionalidad', data['nationality'], 'letters|len:2|custom', self._validate_nationality],
            ['Distrito', data['district'], 'digits|len:1|custom', self._validate_district],
            ['Sexo', data['gender'], 'digits|len:1|custom', self._validate_sex]
        ], self.request.app.db)

    @staticmethod
    async def _validate_sex(name: str, value: str, *args):
        try:
            parse_data_key(int(value), 'sexes')
        except KeyError:
            return '{} ingresado no es correcto'.format(name)

    @staticmethod
    async def _validate_email(name: str, value: str, pos: int, elems: list, dbi: PoolConnectionHolder, user_id: int):
        query = '''
            SELECT true
            FROM usuario
            WHERE id != $1 AND
                  correo_electronico = $2
        '''

        async with dbi.acquire() as connection:
            statement = await connection.prepare(query)
            status = await statement.fetchval(user_id, value)

        status = status or False

        if status:
            return 'El correo electrónico {} ya se encuentra en uso por otro usuario'.format(value)

    @staticmethod
    async def _validate_district(name: str, value: str, *args):
        try:
            parse_data_key(int(value), 'districts')
        except KeyError:
            return '{} ingresado no es correcto'.format(name)

    @staticmethod
    async def _validate_nationality(name: str, value: str, *args):
        try:
            parse_data_key(value, 'nationalities')
        except KeyError:
            return '{} ingresada no es correcto'.format(name)

    async def update(self, id_: int, name: str, last_name: str,
                     address: str, email: str, phone: int,
                     nationality: str, district: int, gender: int):
        query = '''
            UPDATE usuario 
            SET nombres = $2, apellidos = $3, direccion = $4, correo_electronico = $5, nro_telefono = $6,
                nacionalidad = $7, distrito = $8, sexo = $9
            WHERE id = $1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(id_, name, last_name,
                                                                 address, email, phone,
                                                                 nationality, district, gender)


class User(View):
    async def fetch_user(self, user: int, school: int):
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare('''
                SELECT id, nombres, apellidos, rol_id, sexo, tipo_documento, nacionalidad, correo_electronico,
                       escuela, nro_telefono, distrito, direccion, avatar, autorizado, deshabilitado
                FROM usuario
                WHERE id = $1 AND
                      escuela = $2
                LIMIT 1
            ''')).fetchrow(user, school)

    async def get_user(self, user: int, school: int):
        _user = await self.fetch_user(user, school)

        if not _user:
            raise HTTPNotFound

        return _user

    async def fetch_roles(self):
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare('''
                SELECT *
                FROM rol_usuario
            ''')).fetch()

    async def get_roles(self):
        return flatten(await self.fetch_roles() or [], {})

    @staticmethod
    async def _validate_email(name: str, value: str, pos: int, elems: list, dbi: PoolConnectionHolder, user_id: int):
        query = '''
                SELECT true
                FROM usuario
                WHERE id != $1 AND
                      correo_electronico = $2
            '''

        async with dbi.acquire() as connection:
            statement = await connection.prepare(query)
            status = await statement.fetchval(user_id, value)

        status = status or False

        if status:
            return 'El correo electrónico {} ya se encuentra en uso por otro usuario'.format(value)

    @staticmethod
    async def _validate_role(name: str, value: str, pos: int, elems: list, dbi: PoolConnectionHolder,
                             user_role: int, self_role: int):
        if user_role == 4 and self_role != 4:
            return 'No tienes permisos suficientes para cambiar el rol de este usuario'

        if int(value) == 4 and self_role != 4:
            return 'No tienes permisos suficientes para asignar este rol'

        async with dbi.acquire() as connection:
            roles = await (await connection.prepare('''
                SELECT *
                FROM rol_usuario
            ''')).fetch()

        roles = flatten(roles, {}) if roles else []

        error = True
        for role in roles:
            if int(value) == role['id']:
                error = False

        if error:
            return '{}: {} no existe...'.format(name, value)

    @staticmethod
    async def _validate_sex(name: str, value: str, *args):
        try:
            parse_data_key(int(value), 'sexes')
        except KeyError:
            return '{} ingresado no es correcto'.format(name)

    @staticmethod
    async def _validate_district(name: str, value: str, *args):
        try:
            parse_data_key(int(value), 'districts')
        except KeyError:
            return '{} ingresado no es correcto'.format(name)

    @staticmethod
    async def _validate_nationality(name: str, value: str, *args):
        try:
            parse_data_key(value, 'nationalities')
        except KeyError:
            return '{} ingresada no es correcto'.format(name)

    @staticmethod
    async def _validate_authorized(name: str, value: str, *args):
        try:
            parse_data_key(int(value), 'authorized')
        except KeyError:
            return '{} ingresado no es correcto'.format(name)

    @staticmethod
    async def _validate_disabled(name: str, value: str, *args):
        try:
            parse_data_key(int(value), 'disabled')
        except KeyError:
            return '{} ingresado no es correcto'

    @staticmethod
    async def _validate_id(name: str, value: str, pos: int, elems: list, dbi):
        id_type, len_val = int(elems[pos - 1][1]), len(value)

        if id_type == 0:
            if not (8 <= len_val < 10):
                return 'El DNI debe contener 8 o 9 caracteres'
        elif id_type == 1:
            if len_val != 12:
                return 'El Carné de extranjería debe contener 12 caracteres'
        else:
            return 'Ingrese un tipo de documento correcto'

    @staticmethod
    async def _validate_document_type(name: str, value: str, *args):
        if value not in ('0', '1'):
            return '{} debe de ser 0 ó 1'.format(name)


class EditUser(User):
    @view('user.edit')
    @permission_required('mantener_usuarios')
    async def get(self, user: dict):
        _user = await self.get_user(int(self.request.match_info['user']), user['escuela'])

        return {'_user': _user,
                'schools': data_map['schools'],
                'sexes': data_map['sexes'],
                'districts': data_map['districts'],
                'nationalities': data_map['nationalities'],
                'roles': await self.get_roles(),
                '_authorized': data_map['authorized'],
                '_disabled': data_map['disabled']}

    @view('user.edit')
    @permission_required('mantener_usuarios')
    async def post(self, user: dict):
        _user = await self.get_user(int(self.request.match_info['user']), user['escuela'])
        display_data = {
            '_user': _user,
            'schools': data_map['schools'],
            'sexes': data_map['sexes'],
            'districts': data_map['districts'],
            'nationalities': data_map['nationalities'],
            'roles': await self.get_roles(),
            '_authorized': data_map['authorized'],
            '_disabled': data_map['disabled']
        }

        data = await self.request.post()

        if not check_form_data(data, 'name', 'last_name', 'email', 'password', 'role', 'sex',
                               'phone', 'district', 'nationality', 'authorized', 'disabled',
                               'address'):
            display_data.update({'error': 'Parámetros enviados no son los requeridos...'})
            return display_data

        errors = await self.validate(data, _user['id'], _user['rol_id'], user['rol_id']) or []

        if data['password'] != '':
            _p_errors = await self.validate_password(data['password'])

            if _p_errors:
                errors.extend(_p_errors)
                password = None
            else:
                password = hashpw(data['password'].encode('utf-8'), gensalt()).decode('utf-8')
        else:
            password = None

        if errors:
            display_data.update({'errors': errors})
            return display_data

        await self.update(data['name'], data['last_name'], data['email'], int(data['role']), int(data['sex']),
                          int(data['phone']), int(data['district']), data['nationality'], int(data['authorized']),
                          int(data['disabled']), data['address'], _user['id'], password=password)

        display_data.update({'success': 'Se ha actualizado al usuario exitosamente',
                             '_user': await self.get_user(int(self.request.match_info['user']), user['escuela'])})
        return display_data

    async def update(self, name: str, last_name: str, email: str, role: int, sex: int, phone: int, district: int,
                     nationality: str, authorized: int, disabled: int, address: str, user: int, password: str = None):
        _s = ',credencial=$13' if password is not None else ''

        statement = '''
            UPDATE usuario
            SET nombres = $1,
                apellidos = $2,
                correo_electronico = $3,
                rol_id = $4,
                sexo = $5,
                nro_telefono = $6,
                distrito = $7,
                nacionalidad = $8,
                autorizado = $9,
                direccion = $11,
                deshabilitado = $10{}
            WHERE id = $12
        '''.format(_s)

        parameters = [name, last_name, email, role, sex, phone, district, nationality, bool(authorized), bool(disabled),
                      address, user]

        if password is not None:
            parameters.append(password)

        async with self.request.app.db.acquire() as connection:
            await connection.execute(statement, *parameters)

    async def validate(self, data: dict, user_id: int, user_role: int, self_role: int):
        return await validator.validate([
            ['Nombres', data['name'], 'len:8,64'],
            ['Apellidos', data['last_name'], 'len:8,64'],
            ['Correo electrónico', data['email'], 'len:14,128|email|custom', self._validate_email, user_id],
            ['Rol', data['role'], 'digits|len:1|custom', self._validate_role, user_role, self_role],
            ['Sexo', data['sex'], 'digits|len:1|custom', self._validate_sex],
            ['Número de teléfono', data['phone'], 'digits|len:9'],
            ['Dirección', data['address'], 'len:8,64'],
            ['Distrito', data['district'], 'digits|len:1,2|custom', self._validate_district],
            ['Nacionalidad', data['nationality'], 'letters|len:2|custom', self._validate_nationality],
            ['Autorizado', data['authorized'], 'digits|len:1|custom', self._validate_authorized],
            ['Deshabilitado', data['disabled'], 'digits|len:1|custom', self._validate_disabled]
        ], self.request.app.db)

    @staticmethod
    async def validate_password(password: str):
        return await validator.validate([
            ['Contraseña', password, 'len:8,16|password']
        ])


class AdminRegisterUser(User):
    @view('user.admin_register')
    @permission_required('mantener_usuarios')
    async def get(self, user: dict):
        return {'schools': data_map['schools'],
                'sexes': data_map['sexes'],
                'districts': data_map['districts'],
                'nationalities': data_map['nationalities'],
                'roles': await self.get_roles(),
                '_authorized': data_map['authorized'],
                '_disabled': data_map['disabled']}

    @view('user.admin_register')
    @permission_required('mantener_usuarios')
    async def post(self, user: dict):
        display_data = {
            'schools': data_map['schools'],
            'sexes': data_map['sexes'],
            'districts': data_map['districts'],
            'nationalities': data_map['nationalities'],
            'roles': await self.get_roles(),
            '_authorized': data_map['authorized'],
            '_disabled': data_map['disabled']
        }

        data = await self.request.post()

        if not check_form_data(data, 'name', 'last_name', 'email', 'password', 'role', 'sex',
                               'phone', 'district', 'nationality', 'authorized', 'disabled',
                               'address', 'id', 'id_type'):
            display_data.update({'error': 'Parámetros enviados no son los requeridos...'})
            return display_data

        errors = await self.validate(data, 1, user['rol_id'])

        if errors:
            display_data.update({'errors': errors})
            return display_data

        await self.create(data, user)

        display_data.update({'success': 'Se ha creado al usuario exitosamente'})
        return display_data

    async def create(self, data: dict, user: dict):
        statement = '''
            INSERT INTO usuario
            VALUES($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)
        '''
        now = datetime.utcnow() - timedelta(hours=5)
        async with self.request.app.db.acquire() as connection:
            return await connection.execute(statement, int(data['id']), int(data['role']), data['email'],
                                            hashpw(data['password'].encode('utf-8'), gensalt()).decode('utf-8'),
                                            data['name'], data['last_name'], int(data['sex']), int(data['id_type']),
                                            data['nationality'], user['escuela'], int(data['phone']),
                                            int(data['district']), data['address'], None, now, now,
                                            bool(int(data['authorized'])), bool(int(data['disabled'])))

    async def validate(self, data: dict, user_role: int, self_role: int):
        return await validator.validate([
            ['Tipo de documento', data['id_type'], 'digits|len:1|custom', self._validate_document_type],
            ['DNI o Carné de extranjería', data['id'], 'digits|custom|unique:id<int>,usuario', self._validate_id],
            ['Contraseña', data['password'], 'len:8,16|password'],
            ['Nombres', data['name'], 'len:8,64'],
            ['Apellidos', data['last_name'], 'len:8,64'],
            ['Correo electrónico', data['email'], 'len:14,128|email|unique:correo_electronico,usuario'],
            ['Rol', data['role'], 'digits|len:1|custom', self._validate_role, user_role, self_role],
            ['Sexo', data['sex'], 'digits|len:1|custom', self._validate_sex],
            ['Número de teléfono', data['phone'], 'digits|len:9'],
            ['Dirección', data['address'], 'len:8,64'],
            ['Distrito', data['district'], 'digits|len:1,2|custom', self._validate_district],
            ['Nacionalidad', data['nationality'], 'letters|len:2|custom', self._validate_nationality],
            ['Autorizado', data['authorized'], 'digits|len:1|custom', self._validate_authorized],
            ['Deshabilitado', data['disabled'], 'digits|len:1|custom', self._validate_disabled]
        ], self.request.app.db)


class RemoveAvatar(User):
    @pass_user
    @permission_required('mantener_usuarios')
    async def get(self, user: dict):
        _user = await self.get_user(int(self.request.match_info['user']), user['escuela'])

        await self.update(_user['id'])

        raise HTTPFound('/users/{user}/edit'.format(user=_user['id']))

    async def update(self, user: int):
        async with self.request.app.db.acquire() as connection:
            return await connection.execute('''
                UPDATE usuario
                SET avatar = NULL
                WHERE id = $1
            ''', user)


class RegisterStudent(User):
    @pass_user
    @permission_required('mantener_usuarios')
    async def get(self, user: dict):
        _user = await self.get_user(int(self.request.match_info['user']), user['escuela'])

        if _user['rol_id'] != 1:
            raise HTTPNotFound

        try:
            await self.update(_user['id'], user['escuela'])
        except:
            pass

        raise HTTPFound('/users/{user}/edit'.format(user=_user['id']))

    async def update(self, user: int, school: int):
        async with self.request.app.db.acquire() as connection:
            return await connection.execute('''
                WITH ciclo_academico AS (
                    SELECT *
                    FROM ciclo_academico
                    WHERE escuela = $1 AND
                          fecha_comienzo <= $2 AND
                          fecha_fin >= $2
                    LIMIT 1
                )
                
                INSERT INTO matricula (estudiante_id, ciclo_acad_id)
                VALUES ($3, (SELECT id FROM ciclo_academico))
            ''', school, datetime.utcnow() - timedelta(hours=5), user)


class Welcome(View):
    @view('user.welcome')
    async def get(self, user: dict):
        return {}


routes = {
    'login': Login,
    'logout': Logout,
    'register': Registration,
    'recover-password': RecoverPassword,
    'settings': {
        'update-avatar': UpdateAvatar,
        'change-password': ChangePassword,
        'edit-profile': EditProfile
    },
    'users/list':  UsersList,
    'users/list/page-{page:[1-9][0-9]*}': UsersList,
    'users/{user:[1-9][0-9]*}/edit': EditUser,
    'users/{user:[1-9][0-9]*}/remove-avatar': RemoveAvatar,
    'users/{user:[1-9][0-9]*}/register-student': RegisterStudent,
    'users/create-new': AdminRegisterUser,
    'profile/{_user_id:[0-9]+}': ReadProfile,
    'upload-application': UploadApplication,
    '/': Welcome
}
