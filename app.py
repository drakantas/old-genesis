import asyncio
import asyncpg

from pathlib import Path
from jinja2 import FileSystemLoader
from aiohttp.web import Application, run_app
from aiohttp_jinja2 import setup as jinja_setup
from aiohttp_session import setup as db_session_setup

from utils import router, database_session
from config import *

app = Application()

app.db = None

# Temporal, cambiará bastante en base se desarrolle la abstracción de bd
async def setup_connection_pool(app_: Application):
    if not app_.db:
        app_.db = await asyncpg.create_pool(dsn=db_dsn)

# Registrar Jinja2
jinja_setup(app, loader=FileSystemLoader(templates_path))

# Registrar rutas de módulos
router = router.Router(app)
router.update(modules)
router.register()

# Registrar recursos estáticos
static_resources_path = Path(static_resources_path)
app.router.add_static('/', static_resources_path)


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_connection_pool(app))
    db_session_setup(app, database_session.DatabaseStorage(app.db))
    run_app(app, host=host, port=port)

if __name__ == '__main__':
    main()
