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

        if students:
            students = [student for student in students if student['nombres'] and student['apellidos']]

        return {'students': students}

    async def get_students(self, school: int, amount: int, student_role_id: int = 1):
        query = '''
            SELECT id, nombres, apellidos
            FROM usuario
            WHERE rol_id = $1 AND
                  escuela = $2
            LIMIT $3
        '''
        async with self.request.app.db.acquire() as connection:
            stmt = await connection.prepare(query)
            return await stmt.fetch(student_role_id, school, amount)


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
    },
    "teacher": {
        "attendance": {
            "register": RegisterAttendance,
            "list": ListAttendance
        }
    }
}
