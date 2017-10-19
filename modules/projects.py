from datetime import datetime
from aiohttp.web import View, HTTPNotFound, json_response, HTTPUnauthorized
from asyncpg.pool import PoolConnectionHolder


from utils.validator import validator
from utils.helpers import view, permission_required, flatten, school_term_to_str, pass_user, check_form_data


class Project(View):
    async def check_permissions(self, user: dict):
        if user['permissions']['crear_proyecto'] and self.request.match_info['project'] != 'my-project':
            return False
        elif not user['permissions']['crear_proyecto'] and self.request.match_info['project'] == 'my-project':
            return False
        elif not user['permissions']['crear_proyecto'] and not user['permissions']['revisar_proyectos'] and \
                not user['permissions']['gestionar_proyectos']:
            return False
        return True

    async def get_project(self, user: dict) -> dict:
        if not await self.check_permissions(user):
            raise HTTPUnauthorized

        if self.request.match_info['project'] != 'my-project':
            project = await self.fetch_project_by_id(int(self.request.match_info['project']))

            if not project:
                raise HTTPNotFound

            project = dict(project)
            project['ciclo_str'] = school_term_to_str({k[6:]: v for k, v in project.items() if k.startswith('ciclo_')})

        else:
            school_term = await self.fetch_current_school_term(user['escuela'])

            if not school_term:
                raise HTTPNotFound

            project = await self.fetch_project(user['id'], school_term['id'])

            if not project:
                raise HTTPNotFound

            project = dict(project)

            project['ciclo_fecha_comienzo'] = school_term['fecha_comienzo']
            project['ciclo_fecha_fin'] = school_term['fecha_fin']
            project['ciclo_id'] = school_term['id']
            project['ciclo_str'] = school_term_to_str(school_term)

            del school_term

        if not project:
            raise HTTPNotFound

        project['activo'] = project['ciclo_fecha_comienzo'] <= datetime.utcnow() <= project['ciclo_fecha_fin']

        return flatten(project, {})

    async def get_members(self, project: dict):
        return flatten(await self.fetch_members(project['id']), {})

    @staticmethod
    async def is_member(user: dict, members: list):
        for m in members:
            if m['usuario_id'] != user['id']:
                continue
            else:
                return True
        return False

    async def fetch_current_school_term(self, school: int):
        query = '''
            SELECT *
            FROM ciclo_academico
            WHERE $1 >= fecha_comienzo AND
                  $1 <= fecha_fin AND
                  escuela = $2
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(datetime.utcnow(), school)

    async def school_term(self, st_id: int, school: int):
        query = '''
            SELECT *
            FROM ciclo_academico
            WHERE id = $1 AND
                  escuela = $2
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(st_id, school)

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

    async def fetch_project_by_id(self, project: int):
        query = '''
            SELECT proyecto.id, proyecto.titulo, ciclo_academico.fecha_comienzo as ciclo_fecha_comienzo,
            ciclo_academico.fecha_fin as ciclo_fecha_fin, ciclo_academico.id as ciclo_id
            FROM proyecto
            INNER JOIN ciclo_academico
                    ON ciclo_academico.id = proyecto.ciclo_acad_id
            WHERE proyecto.id = $1
            LIMIT 1
        '''

        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(project)

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
            SELECT usuario_id, CASE WHEN usuario.tipo_documento = 0 THEN 'DNI' ELSE 'Carné de extranjería' END
                   as tipo_documento, nombres, apellidos
            FROM integrante_proyecto
            LEFT JOIN usuario
                   ON usuario.id = integrante_proyecto.usuario_id
            WHERE integrante_proyecto.proyecto_id = $1 AND
                  integrante_proyecto.aceptado = true
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(project)

    async def fetch_review(self, project: int, author: int, review: int,
                           is_published: bool = True, is_empty: bool = True):
        if is_empty:
            _is_empty_q = 'AND contenido IS NULL'
        else:
            _is_empty_q = ''

        query = '''
            SELECT *
            FROM observacion_proyecto
            WHERE proyecto_id = $1 AND
                  usuario_id = $2 AND
                  id = $3 AND
                  finalizado = $4{0}
            LIMIT 1
        '''.format(_is_empty_q)

        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(project, author, review, is_published)


class CreateProject(Project):
    @view('projects.create')
    @permission_required('crear_proyecto')
    async def get(self, user: dict):
        school_term = await self.fetch_current_school_term(user['escuela'])

        if not school_term:
            return {'error': 'No se encontró un ciclo académico'}

        project = await self.fetch_project(user['id'], school_term['id'])

        if project:
            return {'error': 'Ya tienes un proyecto registrado'}

        return {'students': await self.fetch_fellas(school_term['id'])}

    @view('projects.create')
    @permission_required('crear_proyecto')
    async def post(self, user: dict):
        school_term = await self.fetch_current_school_term(user['escuela'])

        if not school_term:
            return {'error': 'No se encontró un ciclo académico'}

        project = await self.fetch_project(user['id'], school_term['id'])

        if project:
            return {'error': 'Ya tienes un proyecto registrado'}

        data = await self.request.post()

        if not check_form_data(data, 'title', 'partner'):
            return {'error': 'Data enviada no es correcta',
                    'students': await self.fetch_fellas(school_term['id'])}

        students = await self.fetch_fellas(school_term)

        errors = await self.validate(data, students)

        await self.create(data, school_term['id'], user['id'])

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


class RegisterReview(Project):
    @pass_user
    async def post(self, user: dict):
        # No puedes ver tu propio proyecto, porque esta vista es solo accesible por evaluadores
        if self.request.match_info['project'] == 'my-project':
            raise HTTPNotFound

        student_id = int(self.request.match_info['project'])
        review_id = int(self.request.match_info['review'])

        school_term = await self.fetch_current_school_term(user['escuela'])

        if not school_term:
            return json_response({'message': 'No se encontró ciclo académico para la fecha y hora actual'}, status=400)

        project = await self.fetch_project(student_id, school_term)

        if not project:
            return json_response({'message': 'No se encontró el proyecto para el estudiante pasado para el '
                                             'ciclo académico'}, status=400)

        review = await self.fetch_review(project['id'], user['id'], review_id, is_published=False, is_empty=True)

        if not review:
            return json_response({'message': 'No se encontró la observación seleccionada'}, status=400)

        data = await self.request.post()

        if not check_form_data(data, 'body'):
            return json_response({'message': 'Data malformada...'}, status=400)

        errors = await self.validate(data)

        if errors:
            return json_response({'message': errors[0]}, status=400)

        await self.update(review['id'], data['body'])

        return json_response({'message': 'Se registró la observación de tesis exitosamente'})

    async def validate(self, data: dict):
        return await validator.validate([
            ['Observación', data['body'], 'len:16,4096']
        ], self.request.app.db)

    async def update(self, review: int, body: str):
        async with self.request.app.db.acquire() as connection:
            return await connection.execute('''
                UPDATE observacion_proyecto
                SET contenido = $1 AND
                    finalizado = true
                WHERE id = $2
            ''', body, review)


class ProjectOverview(Project):
    @view('projects.overview')
    async def get(self, user: dict):
        project = await self.get_project(user)
        members = await self.get_members(project)

        return {'project': project,
                'members': members,
                'is_member': await self.is_member(user, members),
                'location': 'overview'}


class ProjectReviews(Project):
    @view('projects.reviews')
    async def get(self, user: dict):
        project = await self.get_project(user)
        members = await self.get_members(project)

        return {'project': project,
                'members': members,
                'is_member': await self.is_member(user, members),
                'location': 'reviews'}


class ProjectFiles(Project):
    @view('projects.files')
    async def get(self, user: dict):
        project = await self.get_project(user)
        members = await self.get_members(project)

        return {'project': project,
                'members': members,
                'is_member': await self.is_member(user, members),
                'location': 'files'}


routes = {
    'projects': {
        'create-new': CreateProject,
        '{project:(?:[1-9][0-9]*|my-project)}': {
            'overview': ProjectOverview,
            'reviews': ProjectReviews,
            'files': ProjectFiles,
            'review-{review:[1-9][0-9]*}': RegisterReview
        }
    }
}
