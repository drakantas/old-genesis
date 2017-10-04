class Attendance
{
    constructor()
    {
        this.fetchSingleReport('2005204664');
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

        if (school_term === null) {
            endpoint = this.studentReport(student);
        }
        else {
            endpoint = this.studentReportFromSchoolTerm(student, school_term);
        }

        axios.get(endpoint)
            .then(function (response) {
                console.log(response, response.data);
                $('#student_attendance_report').modal();
            })
            .catch(function (error) {
                console.log(error);
            });
    }
}

const attendance = new Attendance();
