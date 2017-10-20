from datetime import datetime
from aiohttp.web import View, HTTPNotFound, json_response, HTTPUnauthorized
from asyncpg.pool import PoolConnectionHolder
from typing import Generator


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
            project = await self.fetch_project_by_id(int(self.request.match_info['project']), user['escuela'])

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

    async def get_reviews(self, project: int):
        reviews = await self.fetch_project_reviews(project)
        return list(reviews)

    async def get_review(self, project: int):
        review = await self.fetch_review_by_id(project, int(self.request.match_info['review']))

        if not review:
            raise HTTPNotFound

        if review['contenido'] == '' or not review['finalizado']:
            return json_response({'message': 'Observación pendiente por ser realizada'}, status=412)

        author = {k[6:]: v for k, v in review.items() if k.startswith('autor_')}

        review = {k: v for k, v in review.items() if not k.startswith('autor_')}
        review['author'] = author

        del author
        return json_response(review)

    async def get_pending_reviews(self, user):
        reviews = await self.fetch_pending_reviews(user['id'], user['escuela'])

        if not reviews:
            return False

        return reviews

    async def fetch_decision_panel(self, school: int):
        query = '''
            SELECT usuario.id, nombres, apellidos, rol_usuario.desc as rol
            FROM usuario
            LEFT JOIN rol_usuario
                   ON rol_usuario.id = usuario.rol_id
            WHERE usuario.rol_id = 5 AND
                  usuario.deshabilitado = false AND
                  usuario.autorizado = true AND
                  usuario.escuela = $1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school)

    async def fetch_reviewers(self, school: int):
        query = '''
            SELECT usuario.id, nombres, apellidos, rol_usuario.desc as rol
            FROM usuario
            LEFT JOIN rol_usuario
                   ON rol_usuario.id = usuario.rol_id
            WHERE usuario.deshabilitado = false AND
                  usuario.autorizado = true AND
                  usuario.escuela = $1 AND
                  rol_usuario.revisar_proyectos = true
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school)

    async def fetch_pending_reviews(self, user: int, school: int):
        query = '''
            SELECT observacion_proyecto.proyecto_id, proyecto.titulo as proyecto_titulo, 
                   observacion_proyecto.finalizado, observacion_proyecto.usuario_id as autor_id,
                   observacion_proyecto.id,
                   (SELECT STRING_AGG(CONCAT(usuario.nombres, ' ', usuario.apellidos), '<br />')
                    FROM integrante_proyecto
                    LEFT JOIN usuario ON usuario.id = integrante_proyecto.usuario_id
                    WHERE integrante_proyecto.proyecto_id = observacion_proyecto.proyecto_id AND
                          integrante_proyecto.aceptado = true) as proyecto_integrantes
            FROM observacion_proyecto
            LEFT JOIN proyecto
                   ON proyecto.id = observacion_proyecto.proyecto_id
            WHERE observacion_proyecto.usuario_id = $1 AND
                  proyecto.ciclo_acad_id = (SELECT id FROM ciclo_academico
                                            WHERE ciclo_academico.fecha_comienzo <= $2 AND
                                                  ciclo_academico.fecha_fin >= $2 AND
                                                  ciclo_academico.escuela = $3
                                            LIMIT 1) AND
                  observacion_proyecto.finalizado = false
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(user, datetime.utcnow(), school)

    async def fetch_project_reviews(self, project: int):
        query = '''
            SELECT observacion_proyecto.id, usuario.nombres, usuario.apellidos, rol_usuario.desc as rol, proyecto_id, finalizado
            FROM observacion_proyecto
            INNER JOIN usuario
                    ON usuario.id = observacion_proyecto.usuario_id
            LEFT JOIN rol_usuario
                   ON rol_usuario.id = usuario.rol_id
            WHERE proyecto_id = $1
            ORDER BY observacion_proyecto.id DESC
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(project)

    async def fetch_review_by_id(self, project: int, review: int):
        query = '''
            SELECT observacion_proyecto.contenido, usuario.id as autor_id,
                   rol_usuario.desc as autor_rol, usuario.nombres as autor_nombres,
                   usuario.apellidos as autor_apellidos, observacion_proyecto.finalizado
            FROM observacion_proyecto
            INNER JOIN proyecto
                    ON proyecto.id = observacion_proyecto.proyecto_id
            INNER JOIN usuario
                    ON usuario.id = observacion_proyecto.usuario_id
            LEFT JOIN rol_usuario
                   ON rol_usuario.id = usuario.rol_id
            WHERE proyecto.id = $1 AND
                  observacion_proyecto.id = $2
            LIMIT 1
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(project, review)

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

    async def fetch_project_by_id(self, project: int, school: int):
        query = '''
            SELECT proyecto.id, proyecto.titulo, ciclo_academico.fecha_comienzo as ciclo_fecha_comienzo,
            ciclo_academico.fecha_fin as ciclo_fecha_fin, ciclo_academico.id as ciclo_id
            FROM proyecto
            INNER JOIN ciclo_academico
                    ON ciclo_academico.id = proyecto.ciclo_acad_id
            WHERE proyecto.id = $1 AND
                  ciclo_academico.escuela = $2
            LIMIT 1
        '''

        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetchrow(project, school)

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


class ProjectsList(View):
    @view('projects.list')
    async def get(self, user: dict):
        if 'school_term' in self.request.match_info:
            school_term = await self.fetch_school_term(user['escuela'], int(self.request.match_info['school_term']))
        else:
            school_term = await self.fetch_school_term(user['escuela'])

        if not school_term:
            return {'error': 'No se encontró un ciclo académico'}

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

        return {'projects': _projects,
                'school_terms': await self.get_school_terms(user),
                'current_school_term_id': school_term}

    async def get_school_terms(self, user: dict):

        def _g(stl: list) -> Generator:
            for st in stl:
                yield st['id'], school_term_to_str(st)

        return list(_g(await self._get_school_terms(user['escuela'])))

    async def _get_school_terms(self, school: int):
        query = '''
            SELECT id, fecha_comienzo, fecha_fin
            FROM ciclo_academico
            WHERE ciclo_academico.escuela = $1
            ORDER BY id DESC
            LIMIT 10
        '''
        async with self.request.app.db.acquire() as connection:
            return await (await connection.prepare(query)).fetch(school)

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
                WHERE id = $1 AND
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

        students = await self.fetch_fellas(school_term['id'])

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


class PendingReviewsList(Project):
    @view('projects.pending_reviews')
    @permission_required('revisar_proyectos')
    async def get(self, user: dict):
        return {'reviews': await self.get_pending_reviews(user)}


class SingleReview(Project):
    @pass_user
    async def get(self, user: dict):
        project = await self.get_project(user)

        return await self.get_review(project['id'])

    @pass_user
    async def post(self, user: dict):
        # No puedes ver tu propio proyecto, porque esta vista es solo accesible por evaluadores
        if self.request.match_info['project'] == 'my-project':
            raise HTTPNotFound

        school_term = await self.fetch_current_school_term(user['escuela'])

        if not school_term:
            return json_response({'message': 'No se encontró ciclo académico para la fecha y hora actual'}, status=400)

        project = await self.fetch_project_by_id(int(self.request.match_info['project']), user['escuela'])

        if not project:
            return json_response({'message': 'No se encontró el proyecto para el estudiante pasado para el '
                                             'ciclo académico'}, status=400)

        review = await self.fetch_review(project['id'], user['id'], int(self.request.match_info['review']),
                                         is_published=False, is_empty=True)

        if not review:
            return json_response({'message': 'No se encontró la observación seleccionada'}, status=400)

        data = await self.request.post()

        if not check_form_data(data, 'body'):
            return json_response({'message': 'Data malformada...'}, status=400)

        body = data['body'].replace('<p><br></p>', '')

        errors = await self.validate(body)

        if errors:
            return json_response({'message': errors[0]}, status=400)

        await self.update(review['id'], body)

        del body

        return json_response({'message': 'Se registró la observación de tesis exitosamente'})

    async def validate(self, body: str):
        return await validator.validate([
            ['Observación', body, 'len:16,4096']
        ], self.request.app.db)

    async def update(self, review: int, body: str):
        async with self.request.app.db.acquire() as connection:
            return await connection.execute('''
                    UPDATE observacion_proyecto
                    SET contenido = $2,
                        finalizado = true
                    WHERE id = $1
                ''', review, body)


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
        reviews = await self.get_reviews(project['id'])

        return {'project': project,
                'members': members,
                'reviews': reviews,
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


class GetDecisionPanel(Project):
    @pass_user
    @permission_required('gestionar_proyectos')
    async def get(self, user: dict):
        decision_panel = await self.fetch_decision_panel(user['escuela'])

        if not decision_panel:
            return json_response({'message': 'No se ha encontrado ningún jurado registrado.'}, status=412)

        return json_response(flatten(decision_panel, {}))


class GetReviewers(Project):
    @pass_user
    @permission_required('gestionar_proyectos')
    async def get(self, user: dict):
        reviewers = await self.fetch_reviewers(user['escuela'])

        if not reviewers:
            return json_response({'message': 'No se ha encontrado personal con permisos para realizar observaciones.'},
                                 status=412)

        return json_response(flatten(reviewers, {}))


routes = {
    'projects': {
        'create-new': CreateProject,
        '{project:(?:[1-9][0-9]*|my-project)}': {
            'overview': ProjectOverview,
            'reviews': ProjectReviews,
            'files': ProjectFiles,
            'review/{review:[1-9][0-9]*}': SingleReview
        },
        'pending-reviews': PendingReviewsList,
        'list': ProjectsList,
        'list/school-term-{school_term:[1-9][0-9]*}': ProjectsList
    },
    'reviewers': GetReviewers,
    'decision-panel': GetDecisionPanel
}
