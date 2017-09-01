from jinja2 import FileSystemLoader
from aiohttp.web import Application, run_app
from aiohttp_jinja2 import setup as jinja_setup

from utils import router
from modules import users

host = '127.0.0.1'
port = 80
templates_path = 'views'
modules = (users,)

app = Application()

jinja_setup(app, loader=FileSystemLoader(templates_path))

router = router.Router(app)

router.update(modules)

router.register()

if __name__ == '__main__':
    run_app(app, host=host, port=port)
