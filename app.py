from aiohttp.web import Application, run_app

from modules import users
from utils import router

host = '127.0.0.1'
port = 80
modules = (users,)

app = Application()

router = router.Router(app)

router.update(modules)

router.register()

if __name__ == '__main__':
    run_app(app, host=host, port=port)
