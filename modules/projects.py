from datetime import datetime
from aiohttp.web import View, HTTPNotFound, json_response
from asyncpg.pool import PoolConnectionHolder


from utils.validator import validator
from utils.helpers import view, permission_required, flatten, school_term_to_str


class Project(View):
    async def fetch_current_school_term(self, school: int):
        query = '''
            SELECT id
            FROM ciclo_academico
            WHERE $1 >= fecha_comienzo AND
                  $1 <= fecha_fin AND
                  escuela = $2
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(datetime.utcnow(), school)

    async def school_term(self, st_id: int, school: int):
        query = '''
            SELECT id
            FROM ciclo_academico
            WHERE id = $1 AND
                  escuela = $2
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchval(st_id, school)

    async def fetch_school_term(self, st_id: int, school: int):
        query = '''
            SELECT *
            FROM ciclo_academico
            WHERE id = $1 AND
                  escuela = $2
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(st_id, school)

    async def fetch_project(self, student: int, school_term: int):
        query = '''
            SELECT proyecto.id, proyecto.titulo
            FROM integrante_proyecto
            INNER JOIN proyecto
                    ON proyecto.id = integrante_proyecto.proyecto_id
            WHERE integrante_proyecto.usuario_id = $2 AND
                  proyecto.ciclo_acad_id = $1 AND
                  integrante_proyecto.aceptado = true
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(school_term, student)

    async def fetch_fellas(self, school_term: int):
        query = '''
            SELECT usuario.id, nombres, apellidos
            FROM usuario
            RIGHT JOIN matricula
                    ON matricula.estudiante_id = usuario.id AND
                       matricula.ciclo_acad_id = $1
            LEFT JOIN integrante_proyecto
                   ON integrante_proyecto.usuario_id = usuario.id
            WHERE usuario.deshabilitado = false AND
                  usuario.autorizado = true AND
                  usuario.rol_id = 1 AND
                  matricula.ciclo_acad_id = $1 AND
                 (integrante_proyecto.aceptado = false OR integrante_proyecto.aceptado IS NULL)
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school_term)

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


class CreateProject(Project):
    @view('projects.create')
    @permission_required('crear_proyecto')
    async def get(self, user: dict):
        school_term = await self.fetch_current_school_term(user['escuela'])

        if not school_term:
            return {'error': 'No se encontró un ciclo académico'}

        project = await self.fetch_project(user['id'], school_term)

        if project:
            return {'error': 'Ya tienes un proyecto registrado'}

        return {'students': await self.fetch_fellas(school_term)}

    @view('projects.create')
    @permission_required('crear_proyecto')
    async def post(self, user: dict):
        school_term = await self.fetch_current_school_term(user['escuela'])

        if not school_term:
            return {'error': 'No se encontró un ciclo académico'}

        project = await self.fetch_project(user['id'], school_term)

        if project:
            return {'error': 'Ya tienes un proyecto registrado'}

        data = await self.request.post()

        if not('partner' in data and 'title' in data):
            return {'error': 'Data enviada no es correcta',
                    'students': await self.fetch_fellas(school_term)}

        students = await self.fetch_fellas(school_term)

        errors = await self.validate(data, students)

        await self.create(data, school_term, user['id'])

        if errors:
            return {'errors': errors,
                    'students': students}

        return {'students': students,
                'success': 'Has registrado tu proyecto exitosamente'}

    async def create(self, data: dict, school_term: int, user: int):

        query_params = [data['title'], school_term, user, datetime.utcnow()]

        if data['partner'] == '0':
            with_partner = ''
        else:
            with_partner = ', ($5, (SELECT id FROM proyecto), $4, false)'
            query_params.append(int(data['partner']))

        query = '''
            WITH proyecto AS (
                INSERT INTO proyecto (titulo, ciclo_acad_id)
                VALUES ($1, $2)
                RETURNING id
            )
            INSERT INTO integrante_proyecto (usuario_id, proyecto_id, fecha_integrar, aceptado)
            VALUES($3, (SELECT id FROM proyecto), $4, true){0}
        '''.format(with_partner)

        async with self.request.app.db.acquire() as connection:
            return await connection.execute(query, *query_params)

    async def validate(self, data: dict, students: list):
        validation_groups = [
            ['Título', data['title'], 'len:16,128|unique:titulo,proyecto'],
        ]

        if '0' != data['partner']:
            validation_groups.append(['Compañero(a)', data['partner'], 'digits|len:8,12|custom',
                                      self._validate_partner, students])

        return await validator.validate(validation_groups, self.request.app.db)

    @staticmethod
    async def _validate_partner(name: str, value: str, pos: int, elems: list, dbi: PoolConnectionHolder,
                                students: list):

        student_id = int(value)

        for student in students:
            if student['id'] != student_id:
                continue
            else:
                return

        return '{} ingresado ya forma parte de otro equipo'.format(name)


class OverviewProject(Project):
    @view('projects.overview')
    async def get(self, user: dict):
        # Falta consultar por ciclos académicos por id si es pasado por la URI
        school_term = await self.fetch_current_school_term(user['escuela'])

        if not school_term:
            return {'error': 'No se encontró un ciclo académico'}

        if 'student' in self.request.match_info:
            project = await self.fetch_project(int(self.request.match_info['student']), school_term)

            if not project:
                return {'error': 'No se encontró el proyecto. Es posible que el usuario no exista '
                                 'o no haya registrado un proyecto aún'}
        else:
            project = await self.fetch_project(user['id'], school_term)

            if not project:
                return {'error': 'No tienes un proyecto registrado'}

        school_term = await self.fetch_school_term(school_term, user['escuela'])
        _school_term_str = school_term_to_str(school_term)

        school_term = flatten(school_term, {})
        school_term['str'] = _school_term_str

        del _school_term_str

        project = flatten(project, {})

        project['members'] = flatten(await self.fetch_members(project['id']), {})

        return {'school_term': school_term,
                'project': project}


class RegisterReview(Project):
    async def post(self):
        if self.request.match_info['project'] == 'my-project':
            raise HTTPNotFound

        student_id = int(self.request.match_info['project'])

        school_term = await self.fetch_current_school_term(1)

        if not school_term:
            return json_response({'message': 'No se encontró ciclo académico para la fecha y hora actual'}, status=400)

        project = await self.fetch_project(student_id, school_term)

        if not project:
            return json_response({'message': 'No se encontró el proyecto para el estudiante pasado para el ciclo académico'}, status=400)

        data = await self.request.post()

        if not('review' in data and len(data) == 1):
            return json_response({'message': 'Data malformada...'}, status=400)

        errors = await self.validate(data)

        if errors:
            return json_response({'message': errors[0]}, status=400)

        return json_response({'message': 'Se registró la tesis exitosamente'})

    async def validate(self, data: dict):
        return await validator.validate([
            ['Observación', data['review'], 'len:16,4096']
        ], self.request.app.db)


routes = {
    'projects': {
        'create-new': CreateProject,
        '{project:(?:[1-9][0-9]*|my-project)}': {
            'overview': OverviewProject,
            'review': RegisterReview
        },
    }
}
