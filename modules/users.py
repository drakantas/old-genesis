from aiohttp.web import View
from aiohttp_jinja2 import template as view


class Login(View):
    @view('user/login.html')
    async def get(self) -> None:
        return {}

    @view('user/login.html')
    async def post(self) -> None:
        return

routes = {
    "login": Login
}
