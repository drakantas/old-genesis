from aiohttp.web import View, HTTPNotFound

from utils.helpers import view


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
        
        return {'requested_user': _user}
    
    async def get_user(self, user_id: int):
        query = '''
            SELECT id, nombres, apellidos, direccion, correo_electronico, nro_telefono,
            		nacionalidad, escuela, distrito, sexo
            FROM usuario
            WHERE id = $1
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(user_id)


routes = {
    'profile/{_user_id:[0-9]+}': ReadProfile
}