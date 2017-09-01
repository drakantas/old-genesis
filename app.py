import asyncio
import asyncpg

from pathlib import Path
from jinja2 import FileSystemLoader
from aiohttp.web import Application, run_app
from aiohttp_jinja2 import setup as jinja_setup

from utils import router
from .config import *

app = Application()

# Temporal, cambiará bastante en base se desarrolle la abstracción de bd
async def setup_connection_pool(app_: Application):
    app_.db = await asyncpg.create_pool(dsn=db_dsn)

# Registrar Jinja2
jinja_setup(app, loader=FileSystemLoader(templates_path))

# Registrar rutas de módulos
router = router.Router(app)
router.update(modules)
router.register()

# Registrar recursos estáticos
static_resources_path = Path(static_resources_path)
app.router.add_static('/{}'.format(static_web_path), static_resources_path)


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup_connection_pool(app))
    run_app(app, host=host, port=port)

if __name__ == '__main__':
    main()
