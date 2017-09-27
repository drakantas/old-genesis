from aiohttp.web import View, StreamResponse
from asyncpg.pool import PoolConnectionHolder

from utils.auth import get_auth_data, NotAuthenticated
from utils.map import parse_data_key


class File(View):
    async def get(self):
        file = dict()
        file['id'] = int(self.request.match_info['file_id'])
        file.update(dict(await self.fetch_file_data(file['id'], self.request.app.db)))

        resp = StreamResponse(status=200,
                              reason='OK',
                              headers={'Content-Type': parse_data_key(file['ext'], 'files'),
                                       'Content-Disposition': 'attachment; filename={0}.{1}'.format(file['name'],
                                                                                                    file['ext'])})

        await resp.prepare(self.request)

        resp.write(file['content'])

        await resp.drain()

        return resp

    @staticmethod
    async def fetch_file_data(id_: int, dbi: PoolConnectionHolder) -> bytearray:
        query = '''
            SELECT nombre AS name, ext, contenido AS content
            FROM archivo
            WHERE id=$1
            LIMIT 1
        '''

        async with dbi.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(id_)


routes = {
    "download-file/{file_id:[1-9][0-9]*}": File
}
