class Grades
{
    constructor()
    {
        this.studentBtn = 'button.student_grade_report';
        this.report = '#student_grade_report';
        this.assignGradeBtn = 'button.assign_grade';
        this.assignGrade = '#assign_grade';
        this.myGrades = '#my_grades';

        this.studentBtnSelector = $(this.studentBtn);
        this.myGrades = $(this.myGrades);
        this.reportSelector = $(this.report);

        this.assignGradeBtnSelector = $(this.assignGradeBtn);
        this.assignGradeSelector = $(this.assignGrade);
        this._assign = $('#assign');
        this.cheekyStudentId = null;

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

        if (this.myGrades !== null)
        {
            this.myGrades.on('click', (e) => {
                e.preventDefault();

                $this.fetchStudentGrades('my-own');
                $this.reportSelector.modal();
            });
        }

        this.studentBtnSelector.on('click', (e) => {
            const student = $($(e.currentTarget).parent().parent().find('.student_id')[0]);
            const student_id = student.text();

            const _path = document.location.pathname.split('/');
            const _school_term = _path[_path.length - 1];

            if (_school_term.startsWith('school-term-'))
            {
                $this.fetchStudentGrades(student_id, _school_term.substr(12));
            }
            else
            {
                $this.fetchStudentGrades(student_id);
            }

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

        $('.update_grade').on('click', (e) => {
            $this.handleUpgradeGradeEvent(e);
        });

        $('#update_grade').on('hidden.bs.modal', (e) => {
            const modalBody = $('#update_grade .modal-body');
            modalBody.html('');
        });

        $(document).on('click', '#update_grade button#update', (e) => {
            $this.postUpgradedGrade(e);
        });
    }

    handleUpgradeGradeEvent(e)
    {
        const student = $(e.currentTarget).parent().parent();
        const student_id = student.data('id');

        this.cheekyStudentId = student_id;
        this.getAssignedGrades(student_id, this.handleAssignedGradesResponse);
    }

    postUpgradedGrade(e)
    {
        const form = $('#update_grade .modal-body').find('form')[0];
        const data = new FormData(form);

        const grade_id = $($(form).find('select#grade_id')[0]).find(':selected').val();
        const student_id = this.cheekyStudentId;
        const alert_wrapper = $('#update_grade .modal-body > .alert_wrapper');

        let $this = this;

        axios.post(`/grades/update/${grade_id}/student-${student_id}`, data,
                   {'Content-Type': 'application/x-www-form-urlencoded'})
             .then((response) => {
                 alert_wrapper.html(`<div class="alert alert-success">${response.data.message}</div>`);
             })
             .catch((error) => {
                 const response = error.response;

                 if (response.status !== 400)
                 {
                    console.log(error);
                    return;
                 }

                 let _e_message = null;
                 if (Array.isArray(response.data.message))
                 {
                    let _e = '<ul>';
                    for (const _error of response.data.message) {
                        _e = _e + `<li>${_error}</li>`;
                    }
                    _e = _e + '</ul>';
                    _e_message = _e;
                 }
                 else
                 {
                    _e_message = response.data.message;
                 }

                 alert_wrapper.html(`<div class="alert alert-danger">${_e_message}</div>`);
             });
    }

    getAssignedGrades(student, callback)
    {
        let $this = this;

        axios.get(`/grades/assigned-grades/${student}`)
             .then(function (response) {
                callback($this, response);
             })
             .catch(function (error) {
                callback($this, error.response);
             });
    }

    handleAssignedGradesResponse($this, response)
    {
        const modalBody = $('#update_grade .modal-body');

        if (response.status === 400)
        {
            modalBody.html(`<div class="alert alert-danger">${response.data.message}</div>`);
        }
        else if (response.status === 200)
        {
            modalBody.html($this._updateGradeForm(response.data.grades));
            $(modalBody.find('#grade_id')[0]).selectpicker();
        }

        $('#update_grade').modal();
    }

    _updateGradeForm(grades)
    {
        let _grades = '';

        for (const grade of grades)
        {
            _grades = _grades + `<option value="${grade.id}">${grade.descripcion}</option>`;
        }

        return `
            <div class="alert_wrapper"></div>
            <form>
                <div class="form-group">
                    <label for="grade_id">Nota</label>
                    <select id="grade_id" name="grade_id" class="selectpicker" data-live-search="true" data-width="100%">
                        ${_grades}
                    </select>
                </div>
                <div class="form-group">
                    <label for="score">Puntaje</label>
                    <input id="score" name="score" class="form-control" placeholder="Puntaje" />
                </div>
                <button class="btn btn-success" id="update" type="button">Corregir</button>
            </form>`;
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
