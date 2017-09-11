from uuid import uuid4
from ryoken.json import JSON
from aiohttp.web import Request, Response
from aiohttp_session import AbstractStorage, Session

get_sess_query = '''
    SELECT *
    FROM session
    WHERE id = $1
    LIMIT 1
'''

create_sess_query = '''
    INSERT INTO session (id, data)
    VALUES ($1, $2)
'''

def gen_session_id() -> str:
    return uuid4().hex


class DatabaseStorage(AbstractStorage):
    def __init__(self, connection_pool, cookie_name: str = 'GENESIS_APP', domain=None, max_age=None, path='/',
                 secure=None, httponly=True, encoder=JSON):
        super().__init__(cookie_name=cookie_name, domain=domain, max_age=max_age, path=path, secure=secure,
                         httponly=httponly)
        self._encoder = encoder
        self._db = connection_pool

    async def load_session(self, request: Request):
        cookie = self.load_cookie(request)

        if not cookie:
            return Session(None, data=None, new=True, max_age=self.max_age)

        async with self._db.acquire() as connection:
            stmt = await connection.prepare(get_sess_query)

            data = await stmt.fetchrow(str(cookie))

            if not data:
                return Session(None, data=None, new=True, max_age=self.max_age)

            try:
                data = await self._encoder.decode(data['data'])
            except:
                raise

            return Session(None, data=data, new=False, max_age=self.max_age)

    async def save_session(self, request: Request, response: Response, session: Session):
        session_id = session.identity

        if not session_id:
            session_id = gen_session_id()

            self.save_cookie(response, session_id, max_age=session.max_age)
        else:
            if session.empty:
                self.save_cookie(response, '', max_age=session.max_age)
            else:
                self.save_cookie(response, session_id, max_age=session.max_age)

        data = await self._encoder.encode(self._get_session_data(session))

        async with self._db.acquire() as connection:
            stmt = await connection.prepare(create_sess_query)

            await stmt.fetchrow(session_id, data)
