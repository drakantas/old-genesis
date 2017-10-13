from aiohttp.web import Request
from aiohttp_session import get_session


class NotAuthenticated(Exception):
    pass


async def get_auth_data(request: Request) -> dict:
    session = await get_session(request)

    if 'id' not in session:
        raise NotAuthenticated

    async with request.app.db.acquire() as connection:
        query = '''
            SELECT usuario.id, rol_usuario.desc as rol, correo_electronico,
                   nombres, apellidos, sexo,
                   tipo_documento, nacionalidad, escuela,
                   nro_telefono, distrito, direccion,
                   deshabilitado, avatar
            FROM usuario
            LEFT JOIN rol_usuario
                   ON rol_usuario.id = usuario.rol_id
            WHERE usuario.id = $1 AND
                  deshabilitado != true
        '''
        stmt = await connection.prepare(query)
        user = await stmt.fetchrow(int(session['id']))

        return user
