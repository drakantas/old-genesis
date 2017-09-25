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
            SELECT id, rol_id, correo_electronico,
                   nombres, apellidos, sexo,
                   tipo_documento, nacionalidad, escuela,
                   nro_telefono, distrito, direccion,
                   deshabilitado
            FROM usuario
            WHERE id = $1 AND
                  deshabilitado != true
        '''
        stmt = await connection.prepare(query)
        user = await stmt.fetchrow(int(session['id']))

        return {key: value for key, value in user.items()}
