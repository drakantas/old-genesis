class Grades
{
    constructor()
    {
        this.studentBtn = 'button.student_grade_report';
        this.report = '#student_grade_report';

        this.studentBtnSelector = $(this.studentBtn);
        this.reportSelector = $(this.report);

        this.registerEvents();
    }

    studentReport(id)
    {
        return `/grades/student-report/${id}`;
    }

    studentReportFromSchoolTerm(id, school_term)
    {
        return `/grades/student-report/school-term-${school_term}/${id}`;
    }

    registerEvents()
    {
        let $this = this;

        this.studentBtnSelector.on('click', (e) => {
            const student = $($(e.currentTarget).parent().parent().find('.student_id')[0]);
            const student_id = student.text();

            $this.fetchStudentGrades(student_id);
            $this.reportSelector.modal();
        });
    }

    fetchStudentGrades(student, school_term = null)
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
                $($this.report + ' .modal-body').html($this.buildReport(response.data.grades, response.data.final_grade));
            })
            .catch(function (error) {
                console.log(error);
            });
    }

    buildReport(grades, final_grade)
    {
        let header = '';
        let sub_header = '';
        let body = '';
        let _grades = [];
        let i = 0;

        for (const grade of grades) {
            i += 1;
            if (!Array.isArray(grade)) {
                _grades.push(grade['valor']);
                header = header + `
                    <th rowspan="2">${grade['descripcion']}</th>
                `;
            } else {
                header = header + `
                    <th rowspan="1" colspan="${grade.length}">${grade[0]['grupo']}</th>
                `;
                for (const sub_grade of grade) {
                    _grades.push(sub_grade['valor']);
                    sub_header = sub_header + `
                        <th rowspan="1">${sub_grade['descripcion']}</th>
                    `;
                }
            }
        }

        if (sub_header !== '') {
            sub_header = '<tr>' + sub_header + '</tr>';
        }

        _grades = _grades.map((_value) => {
            return `<td>${_value}</td>`;
        });

        _grades = _grades.join('');

        return `
            <table class="table report">
                <thead>
                    <tr>
                        ${header}
                        <th rowspan="2">Promedio final</th>
                    </tr>
                    ${sub_header}
                </thead>
                <tbody>
                    <tr>
                        ${_grades}
                        <td>${final_grade}</td>
                    </tr>
                </tbody>
            </table>
        `;
    }
}

const grades = new Grades();
