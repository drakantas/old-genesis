class Attendance
{
    constructor()
    {
        this.fetchSingleReport('2003207956');
    }

    studentReport(id)
    {
        return `/attendance/student-report/${id}`;
    }

    studentReportFromSchoolTerm(id, school_term)
    {
        return `/attendance/student-report/school-term-${school_term}/${id}`;
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
                $this.buildReport(response.data.overall, response.data.schedules);
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

    buildReport(overall, schedules)
    {
        let overall_headers = "";
        let overall_body = "";
        let buffer = [];

        if (schedules.length > 0) {
            for (const i of schedules.keys()) {
                overall_headers = overall_headers + `<th colspan="1">Horario ${i + 1}</th>`;
                overall_body = overall_body + `<td colspan="1">${overall[i + 1]}%</td>`;

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
                            <th>Profesor</th>
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
                        <tr>
                            <td rowspan="2">Dr. Susy Bayona</td>
                            <td colspan="1"></td>
                            <td>05:30PM - 07:30 PM</td>
                            <td colspan="5"></td>
                        </tr>
                        <tr>
                            <td colspan="5"></td>
                            <td>05:30PM - 07:30 PM</td>
                            <td colspan="1"></td>
                        </tr>
                    <tr>
                            <td rowspan="1">Dr. Susy Bayona</td>
                            <td colspan="3"></td>
                            <td>05:30PM - 07:30 PM</td>
                            <td colspan="3"></td>
                        </tr>
                        <tr>
                            <td colspan="6"></td>
                            <td>05:30PM - 07:30 PM</td>
                            <td colspan="1"></td>
                        </tr>
                </tbody>
            </table>
        `;
    }
}

const attendance = new Attendance();
