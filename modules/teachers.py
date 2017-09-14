from datetime import datetime
from aiohttp.web import View
from aiohttp_jinja2 import template as view

from utils.auth import get_auth_data, NotAuthenticated


class StudentsList(View):
    @view('teacher/students_list.html')
    async def get(self):
        display_amount = 10

        if 'display_amount' in self.request.match_info:
            display_amount = self.request.match_info['display_amount']
            if display_amount == 'all':
                display_amount = 1000
            else:
                display_amount = int(display_amount)

        user = await get_auth_data(self.request)
        students = await self.get_students(user['escuela'], display_amount)

        return {'students': students}

    async def get_students(self, school: int, amount: int, student_role_id: int = 1, danger: int = 80):
        query = '''
            WITH ciclo_academico AS (
                SELECT fecha_comienzo, fecha_fin
                FROM ciclo_academico
                WHERE $1 >= fecha_comienzo AND
                      $1 <= fecha_fin
                LIMIT 1
            ),
            alumno AS (
                SELECT id, nombres, apellidos, 
                    COALESCE(
                        (SELECT CAST(COUNT(CASE WHEN asistio=true THEN 1 ELSE NULL END) / CAST(COUNT(*) AS FLOAT) * 100 AS INT)
                            FROM asistencia
                            RIGHT JOIN ciclo_academico
                                    ON ciclo_academico.fecha_comienzo <= asistencia.fecha AND
                                       ciclo_academico.fecha_fin >= asistencia.fecha
                       WHERE asistencia.alumno_id = usuario.id
                       HAVING COUNT(*) >= 1),
                    0) AS asistencia,
                    COALESCE(
                        (SELECT id FROM proyecto
                             RIGHT JOIN integrante_proyecto
                                     ON integrante_proyecto.usuario_id = usuario.id),
                    NULL) AS id_proyecto
                FROM usuario
                WHERE rol_id = $2 AND
                      escuela = $3 AND
                      nombres != '' AND
                      apellidos != ''
                LIMIT $4
            )
            SELECT id, nombres, apellidos, asistencia,
                   CASE WHEN asistencia < $5 THEN true ELSE false END as peligro,
                   id_proyecto
              FROM alumno
        '''

        async with self.request.app.db.acquire() as connection:
            stmt = await connection.prepare(query)
            return await stmt.fetch(datetime.utcnow(), student_role_id, school, amount, danger)


class RegisterAttendance(View):
    @view('teacher/register_attendance.html')
    async def get(self):
        return {}


class ListAttendance(View):
    @view('teacher/attendance_list.html')
    async def get(self):
        return {}

    async def get_students_attendances(self):
        query = '''
            SELECT alumno_id, profesor_id, fecha
            FROM asistencia
            WHERE profesor_id = $1 AND
                  fecha >= 
        '''


routes = {
    "students": {
        "list": StudentsList,
        "list/{display_amount:(?:10|25|all)}": StudentsList,
        "register-attendance": RegisterAttendance
    }
}
