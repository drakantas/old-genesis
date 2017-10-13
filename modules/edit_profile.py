from aiohttp.web import View
from asyncpg.pool import PoolConnectionHolder

from utils.helpers import view
from utils.validator import validator


class EditProfile(View):
    @view('user.edit_profile')
    async def get(self, user: dict):
        return {}

    @view('user.edit_profile')
    async def post(self, user: dict):
        display_data = {}

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
            ['Apellidos', data['last_name'], 'len:8,84'],
            ['Dirección', data['address'], 'len:8,84'],
            ['Email', data['email'], 'len:14,128|email|custom', self._validate_email, user_id],
            ['Teléfono', data['phone'], 'digits|len:9'],
            ['Nacionalidad', data['nationality'], 'len:2'],
            ['Distrito', data['district'], 'digits|len:1'],
            ['Sexo', data['gender'], 'digits|len:1']
        ], self.request.app.db)

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


routes = {
    'settings/edit-profile': EditProfile
}
