from aiohttp.web import View, Response


class Login(View):
    async def get(self) -> Response:
        return Response(text='Hola mundo')

    async def post(self) -> Response:
        return Response(text='Hola mundo')

routes = {
    "login": Login
}
