from datetime import datetime
from aiohttp.web import View

from utils.helpers import view, flatten


class ProjectsList(View):
    @view('projects.list')
    async def get(self, user: dict):
        if 'school_term' in self.request.match_info:
            school_term = await self.fetch_school_term(user['escuela'], int(self.request.match_info['school_term']))
        else:
            school_term = await self.fetch_school_term(user['escuela'])

        if not school_term:
            return {'error': ['No se encontró un ciclo académico']}

        projects = await self.fetch_projects(school_term)

        async def enrichen_project(project_: dict):
            _project = flatten(project_, {})

            _project['members'] = flatten(await self.fetch_members(_project['id']), {})
            _project['reviewed'] = await self.fetch_reviews_count(_project['id'])
            _project['decision_panel'] = flatten(await self.fetch_decision_panel(_project['id']), {})
            _project['presentation_date'] = await self.fetch_presentation_date(_project['id'])

            return _project

        _projects = []

        for project in projects:
            _projects.append(await enrichen_project(project))

        del projects

        return {'projects': _projects}

    async def fetch_members(self, project: int):
        query = '''
            SELECT usuario_id, nombres, apellidos
            FROM integrante_proyecto
            LEFT JOIN usuario
                   ON usuario.id = integrante_proyecto.usuario_id
            WHERE integrante_proyecto.proyecto_id = $1 AND
                  integrante_proyecto.aceptado = true
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(project)

    async def fetch_reviews_count(self, project: int):
        query = '''
            SELECT COUNT(true) 
            FROM observacion_proyecto 
            WHERE proyecto_id = $1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(project)

    async def fetch_decision_panel(self, project: int):
        query = '''
            SELECT jurado_id, nombres, apellidos
            FROM jurado_presentacion
            LEFT JOIN usuario
                   ON usuario.id = jurado_presentacion.jurado_id
            WHERE presentacion_id = $1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(project)

    async def fetch_presentation_date(self, project: int):
        query = '''
            SELECT fecha 
            FROM presentacion_proyecto 
            WHERE proyecto_id = $1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(project)

    async def fetch_school_term(self, school: int, school_term: int = None):
        if school_term is None:
            query = '''
                    SELECT id
                    FROM ciclo_academico
                    WHERE $1 >= fecha_comienzo AND
                          $1 <= fecha_fin AND
                          escuela = $2
                    LIMIT 1
            '''
        else:
            query = '''
                SELECT id
                FROM ciclo_academico
                WHERE id = $1
                      escuela = $2
                LIMIT 1
            '''

        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(school_term or datetime.utcnow(), school)

    async def fetch_projects(self, school_term: int):
        query = '''
            SELECT id, titulo, ciclo_acad_id
            FROM proyecto
            WHERE ciclo_acad_id = $1            
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school_term)


routes = {
    'projects': {
        'list': ProjectsList,
        'school-term-{school_term:[1-9][0-9]*}/list': ProjectsList
    }
}
