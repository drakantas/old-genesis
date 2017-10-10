from aiohttp.web import View
from aiohttp_jinja2 import template as view
from utils.validator import validator


class EditProfile(View):
    @view('user.edit_profile')
    async def get(self, user: dict):
        return {}

    @view('user.edit_profile')
    async def post(self, user: dict):
        display_data = {}

        student_id = user['id']

        data = await self.request.post()

        name, last_name, address, email = data['name'], data['last_name'], data['address'], data['email']
        phone, nationality = data['phone'], data['nationality']
        school, district, gender = data['school'], data['district'], data['gender']
        
        errors = await self.validate(name, last_name, address,
                                     email, phone, nationality,
                                     school, district, gender)

        if not errors:
            faculty, district, gender = int(school), int(district), int(gender)

            await self.update(student_id, name, last_name, address,
                              email, phone, nationality, faculty,
                              district, gender)

            display_data['success'] = 'Se han registrado los cambios. Se han actualizado tus datos.'

        else:
            display_data['errors'] = errors

        return display_data

    async def validate(self, name: str, last_name: str, address: str,
                       email: str, phone: str, nationality: str, school: str,
                       district: str, gender: str):
        return await validator.validate([
            ['Nombres', name, 'len:8,64'],
            ['Apellidos', last_name, 'len:8,84'],
            ['Dirección', address, 'len:8,84'],
            ['Email', email, 'len:14,128|email|unique:correo_electronico,usuario'],
            ['Teléfono', phone, 'digits|len:9'],
            ['Nacionalidad', nationality, 'digits|len:2'],
            ['Escuela', school, 'digits|len:1'],
            ['Distrito', district, 'len:8,64'],
            ['Sexo', gender, 'digits|len:1']
        ], self.request.app.db)

    async def update(self, id_: int, name: str, last_name: str,
                     address: str, email: str, phone: int, nationality: str,
                     school: int, district: int, gender: int):
        query = '''
            UPDATE usuario 
            SET nombres = $2, apellidos = $3, direccion = $4, correo_electronico = $5, nro_telefono = $6,
                nacionalidad = $7, escuela = $8, distrito = $9, sexo = $10, credencial = $11
            WHERE id = $1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(id_, name, last_name, address,
                                                                 email, phone, nationality, school,
                                                                 district, gender)


routes = {
    'settings/edit-profile': EditProfile
}
