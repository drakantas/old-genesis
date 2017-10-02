class SchoolTerm
{
    constructor(timetable)
    {
        this.timetable = timetable;
        this.schedules = timetable.find('div[class^="schedule"]');
        this.schedule_counter = this.schedules.length;
        this.addScheduleBtn = $('button.btn-add-item');

        if (this.schedule_counter >= 1) {
            this.schedule_counter -= 1;
        }

        this.registerEvents();
    }

    registerEvents()
    {
        this.addScheduleBtn.on('click', () => {
            this.summonSchedule();
        });

        $(document).on('click', 'div[class^="schedule"] button.btn-remove-item', (e) => {
            let schedule = $(e.currentTarget).parent().parent().parent();
            schedule.remove();
        });
    }

    summonSchedule()
    {
        this.schedule_counter += 1;
        this.addSchedule(this.schedule_counter);
    }

    addSchedule(id)
    {
        let template = this.scheduleTemplate(id);
        this.timetable.append(template);

        for (timeSelector of this.scheduleTimeSelectors(id)) {
            timeSelector.datetimepicker({format: 'LT'});
        }

        for (mixedSelector of this.scheduleTeachersAndDaySelectors(id)) {
            mixedSelector.selectpicker();
        }
    }

    scheduleTeachersAndDaySelectors(id)
    {
        return [
            $(`#schedule_${id}_teacher`),
            $(`#schedule_${id}_day`)
        ];
    }

    scheduleTimeSelectors(id)
    {
        return [
            $(`#schedule_${id}_start_time`).parent(),
            $(`#schedule_${id}_end_time`).parent()
        ];
    }

    getTeachers()
    {
        let schedule = this.schedules[0];
        let teachers = $(schedule).find('[name="schedule_0_teacher"] > option');
        return (typeof teachers !== 'undefined') ? [...teachers] : [];
    }

    scheduleTemplate(id)
    {
        let teachers = this.getTeachers();
        let teachersHtmlString = [];

        if (teachers.length >= 1) {
            for (teacher of teachers) {
                teachersHtmlString.push(teacher.outerHTML);
            }

            teachersHtmlString = teachersHtmlString.join('');
        }

        if (typeof teachersHtmlString === 'object') {
            teachersHtmlString = '';
        }

        return `
            <div class="schedule_${id}">
                <div class="row">
                    <div class="col-xs-1 remove">
                        <button type="button" class="btn btn-remove-item">
                            <span class="glyphicon glyphicon-trash"></span>
                        </button>
                    </div>
                    <div class="col-xs-11">
                        <div class="row">
                            <div class="col-sm-12 teacher-wrapper">
                                <select class="selectpicker" id="schedule_${id}_teacher" name="schedule_${id}_teacher" data-live-search="true" data-width="100%">
                                    ${teachersHtmlString}
                                </select>
                            </div>
                            <div class="col-sm-12 col-md-4">
                                <label for="schedule_${id}_day">Día</label>
                                <select class="selectpicker" id="schedule_${id}_day" name="schedule_${id}_day" data-live-search="true" data-width="100%">
                                    <option value="0">Domingo</option>
                                    <option value="1">Lunes</option>
                                    <option value="2">Martes</option>
                                    <option value="3">Miércoles</option>
                                    <option value="4">Jueves</option>
                                    <option value="5">Viernes</option>
                                    <option value="6">Sábado</option>
                                </select>
                            </div>
                            <div class="col-sm-6 col-md-4">
                                <label for="schedule_${id}_start_time">Hora de inicio</label>
                                <div class="input-group date start_time">
                                    <input type="text" id="schedule_${id}_start_time" name="schedule_${id}_start_time" class="form-control" />
                                    <span class="input-group-addon">
                                        <span class="glyphicon glyphicon-time"></span>
                                    </span>
                                </div>
                            </div>
                            <div class="col-sm-6 col-md-4">
                                <label for="schedule_${id}_end_time">Hora de fin</label>
                                <div class="input-group date end_time">
                                    <input type="text" id="schedule_${id}_end_time" name="schedule_${id}_end_time" class="form-control" />
                                    <span class="input-group-addon">
                                        <span class="glyphicon glyphicon-time"></span>
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
}

const schoolTerm = new SchoolTerm($('.timetable'));
