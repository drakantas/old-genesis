from datetime import datetime
from aiohttp.web import View, HTTPNotFound


from utils.helpers import view


class CreateProject(View):
    @view('projects.create')
    async def get(self, user: dict):
        return {}

    @view('projects.create')
    async def post(self, user: dict):
        return {}


class ViewProject(View):
    @view('projects.view')
    async def get(self, user: dict):
        return {}

    @view('projects.view')
    async def post(self, user: dict):
        return {}


routes = {
    'projects': {
        'create-new': CreateProject,
        'view': {
            'my-project': ViewProject,
            '[0-9][1-9]*': ViewProject
        }
    }
}
