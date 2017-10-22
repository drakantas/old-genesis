from aiohttp.web import View, StreamResponse, HTTPNotFound

from utils.map import parse_data_key
from utils.helpers import pass_user, get_chunks, permission_required


class File(View):
    @pass_user
    @permission_required('autorizar_estudiantes')
    async def get(self, user: dict):
        file = await self.fetch_file(int(self.request.match_info['file']))

        if not file:
            raise HTTPNotFound

        headers = {
            'Content-Type': parse_data_key(file['ext'], 'files'),
            'Content-Disposition': 'attachment; filename={file}'.format(file=file['nombre'])
        }

        response = StreamResponse(status=200, reason='OK', headers=headers)

        chunks = tuple(get_chunks(file['contenido']))

        await response.prepare(self.request)

        for i in range(0, len(chunks)):
            try:
                response.write(chunks[i])

                await response.drain()
            except Exception as e:
                print(repr(e))

        del file, chunks

        return response

    async def fetch_file(self, id_: int) -> dict:
        query = '''
            SELECT CONCAT(archivo.nombre, '.', archivo.ext) as nombre,
                   archivo.contenido, archivo.ext
            FROM archivo
            INNER JOIN solicitud_autorizacion
                    ON solicitud_autorizacion.archivo_id = archivo.id
            WHERE archivo.id = $1
            LIMIT 1
        '''

        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(id_)


routes = {
    "download-file/{file:[1-9][0-9]*}": File
}
