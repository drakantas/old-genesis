class Grades
{
    constructor()
    {
        this.studentBtn = 'button.student_grade_report';
        this.report = '#student_grade_report';
        this.assignGradeBtn = 'button.assign_grade';
        this.assignGrade = '#assign_grade';

        this.studentBtnSelector = $(this.studentBtn);
        this.reportSelector = $(this.report);

        this.assignGradeBtnSelector = $(this.assignGradeBtn);
        this.assignGradeSelector = $(this.assignGrade);
        this._assign = $('#assign');

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

    _assignGrade()
    {
        return `/grades/assign`;
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

        this.assignGradeBtnSelector.on('click', (e) => {
            const student = $($(e.currentTarget).parent().parent().find('.student_id')[0]);
            const student_id = student.text();

            $('#student_id').val(student_id);
            $this.assignGradeSelector.modal();
        });

        this._assign.on('click', (e) => {
            e.preventDefault();

            const data = new FormData(this.assignGradeSelector.find('form')[0]);

            axios.post($this._assignGrade(), data, {
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            }).then(function (response) {
                const success = `
                    <div class="alert alert-success" role="alert">${response.data.success}</div>
                `;

                $($this.assignGradeSelector.find('.alert_wrapper')[0]).html(success);
            }).catch(function (error) {
                const response = error.response;

                if (response.status !== 400) {
                    console.log(error);
                    return;
                }

                const error_message = response.data.error;
                let _error = '';

                if (Array.isArray(error_message)) {
                    _error = `<div class="alert alert-danger" role="alert"><ul>`;
                    for (const e of error_message) {
                        _error = _error + `<li>${e}</li>`;
                    }
                    _error = _error + `</ul></div>`;
                } else {
                    _error = `
                        <div class="alert alert-danger" role="alert">
                            ${error_message}
                        </div>
                    `;
                }

                $($this.assignGradeSelector.find('.alert_wrapper')[0]).html(_error);
            });
        });

        this.assignGradeSelector.on('hidden.bs.modal', function (e) {
            $($this.assignGradeSelector.find('.alert_wrapper')[0]).html('');
            $($this.assignGradeSelector.find('#score')[0]).val('');
            $('#grade_id').val(1);
            $('#grade_id').selectpicker('refresh');
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
                const response = error.response;

                if (response.status !== 400) {
                    console.log(error);
                    return;
                }

                $($this.report + ' .modal-body').html(`
                    <div class="alert alert-danger">
                        ${response.data.message}
                    </div>
                `);
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
