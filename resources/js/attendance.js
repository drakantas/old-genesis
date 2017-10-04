class Attendance
{
    constructor()
    {
        this.registerEvents();
    }

    studentReport(id)
    {
        return `/attendance/student-report/${id}`;
    }

    studentReportFromSchoolTerm(id, school_term)
    {
        return `/attendance/student-report/school-term-${school_term}/${id}`;
    }

    registerEvents()
    {
        let $this = this;

        $('a.attendance-btn').on('click', function(e) {
            const student = $($(e.currentTarget).parent().parent().find('.student_id')[0]);
            const student_id = student.text();

            $this.fetchSingleReport(student_id);

            $('#student_attendance_report').modal();
        });
    }

    fetchSingleReport(student, school_term = null)
    {
        let endpoint = null;
        let $this = this;

        if (school_term === null) {
            endpoint = this.studentReport(student);
        }
        else {
            endpoint = this.studentReportFromSchoolTerm(student, school_term);
        }

        axios.get(endpoint)
            .then(function (response) {
                $('#student_attendance_report .modal-body').html($this.buildReport(response.data.overall, response.data.schedules, response.data.attendances));
            })
            .catch(function (error) {
                console.log(error);
            });
    }

    searchOnBuffer(value, key, buffer)
    {
        for (const i of buffer.keys()) {
            if (typeof buffer[i][0] !== 'undefined') {
                for (const _i of buffer[i].keys()) {
                    for (const k in buffer[i][_i]) {
                        if (k === key && buffer[i][_i][k] === value) return i;
                    }
                }
            }
        }
        return -1;
    }

    convertToTimeStr(time)
    {
        let period = "";

        if (time >= 1200) {
            period = "PM";
        }
        else {
            period = "AM";
        }

        let _time = (time / 100.0) + "";
            _time = _time.split('.');

        let hours = _time[0], minutes = _time[1];

        if (typeof hours === 'undefined') {
            hours = "00";
        }
        else if (hours.length === 1) {
            hours = "0" + hours;
        }

        if (typeof minutes === 'undefined') {
            minutes = "00";
        }
        else if (minutes.length === 0) {
            minutes = minutes + "0";
        }

        return `${hours}:${minutes} ${period}`;
    }

    buildReport(overall, schedules, attendances)
    {
        let overall_headers = "";
        let overall_body = "";
        let buffer = [];
        let _schedules = "";
        let schedule_number_by_teacher = [];

        if (schedules.length > 0) {
            for (const i of schedules.keys()) {
                let p_value = (typeof overall[i + 1] === 'undefined') ? 0 : overall[i + 1];
                overall_headers = overall_headers + `<th colspan="1">Horario ${i + 1}</th>`;
                overall_body = overall_body + `<td colspan="1">${p_value}%</td>`;

                for(const k in schedules[i]) {
                    if (k !== 'profesor_id') continue;
                    const _i = this.searchOnBuffer(schedules[i]['profesor_id'], 'profesor_id', buffer);

                    if (_i !== -1) {
                        buffer[_i].push(schedules[i]);
                    }
                    else {
                        buffer.push([schedules[i]]);
                    }
                }
            }
        }

        if (buffer.length > 0) {
            let schedule_counter = 1;
            for (const teacher_group of buffer) {
                let first = true;
                for (const teacher of teacher_group) {
                    let left_space = (teacher.dia_clase === 0) ? 0 : teacher.dia_clase;
                    let right_space = (7 - teacher.dia_clase) === 0 ? 0 : 7 - teacher.dia_clase;
                    let left = (left_space !== 0) ? `<td colspan="${left_space}"></td>` : '';
                    let right = (right_space !== 0) ? `<td colspan="${right_space}"></td>` : '';
                    if (first) {
                        _schedules = _schedules + `
                            <tr>
                                <td rowspan="${teacher_group.length}">${teacher.profesor_nombres} ${teacher.profesor_apellidos}</td>
                                <td>Horario ${schedule_counter}</td>
                                ${left}
                                <td>${this.convertToTimeStr(teacher.hora_comienzo)} - ${this.convertToTimeStr(teacher.hora_fin)}</td>
                                ${right}
                            </tr>
                        `;
                        schedule_counter += 1;
                        first = false;
                        continue;
                    }
                    _schedules = _schedules + `
                            <tr>
                                <td>Horario ${schedule_counter}</td>
                                ${left}
                                <td>${this.convertToTimeStr(teacher.hora_comienzo)} - ${this.convertToTimeStr(teacher.hora_fin)}</td>
                                ${right}
                            </tr>
                    `;
                    schedule_counter += 1;
                }
            }
        }

        overall['average'] = (typeof overall['average'] === 'undefined') ? 0 : overall['average'];

        let detailed_attendance_list = "";

        for (const schedule of schedules) {
            for (const _schedule_key in attendances) {
                const _schedule_attendances = attendances[_schedule_key];
                if (+_schedule_key === schedule['id']) {
                    for(_sch_att of _schedule_attendances) {
                        detailed_attendance_list = detailed_attendance_list + `
                            <tr><td>${_sch_att['fecha_registro']}</td>
                        `;
                        for (const schedule of schedules) {
                            if (+_schedule_key === schedule['id']) {
                                    if(_sch_att.asistio) {
                                        detailed_attendance_list = detailed_attendance_list + `
                                            <td><span class="glyphicon glyphicon-ok"></span></td>
                                        `;
                                    }
                                    else {
                                        detailed_attendance_list = detailed_attendance_list + `
                                            <td><span class="glyphicon glyphicon-remove"></span></td>
                                        `;
                                    }
                            }
                            else {
                                detailed_attendance_list = detailed_attendance_list + `
                                    <td> - </td>
                                `;
                            }
                        }
                        detailed_attendance_list = detailed_attendance_list + `
                            </tr>
                        `;
                    }
                }
            }
        }

        return `
            <table class="table report">
                <thead>
                        <tr>
                            <th width="50%"></th>
                            ${overall_headers}
                        </tr>
                </thead>
                <tbody>
                        <tr>
                            <td width="50%">
                                ${overall['average']}%
                            </td>
                                ${overall_body}
                        </tr>
                </tbody>
            </table>
            <hr class="divider" />
            <table class="table report">
                <thead>
                        <tr>
                            <th colspan="2">Profesor</th>
                            <th>Domingo</th>
                            <th>Lunes</th>
                            <th>Martes</th>
                            <th>Miércoles</th>
                            <th>Jueves</th>
                            <th>Viernes</th>
                            <th>Sábado</th>
                        </tr>
                </thead>
                <tbody>
                        ${_schedules}
                </tbody>
            </table>
            <hr class="divider" />
            <table class="table report">
                <thead>
                    <tr>
                        <th>Día y hora</th>
                        ${overall_headers}
                    </tr>
                </thead>
                <tbody>
                    ${detailed_attendance_list}
                </body>
            </table>
        `;
    }
}

const attendance = new Attendance();
