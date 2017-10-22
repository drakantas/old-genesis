class GradingStructure
{
    constructor()
    {
        this.groupsCounter = 1;
        this.gradesCounter = 1;

        let $this = this;

        $(document).on('click', 'a#addGrade', (e) => {
            const group = $(e.currentTarget).parent();
            $this.addGrade($this, group);
        });

        $(document).on('click', 'a#addGroup', (e) => {
            $this.addGroup($this);
        });
    }

    addGroup($this)
    {
        const container = $('#gradesContainer');

        $this.groupsCounter += 1;
        $this.gradesCounter += 1;

        container.append($this.group($this.groupsCounter, $this.gradesCounter));
    }

    addGrade($this, group)
    {
        $this.gradesCounter += 1;

        $(group.find('.grades')[0]).append($this.grade($this.gradesCounter, group.data('group')));
    }

    group(groupId, gradeId)
    {
        return `
            <div class="list-group-item grade_group" data-group="${groupId}">
                <input type="text" class="form-control" name="group_${groupId}" style="width:350px;display:inline-block;" placeholder="Nombre de grupo" />
                <a href="javascript:;" class="btn btn-primary" id="addGrade">Agregar nota</a>
                <hr class="divider" />
                <div class="list-group grades">
                    <div class="list-group-item">
                        <div class="row">
                            <div class="col-md-6">
                                <input type="text" class="form-control" name="group_${groupId}_grade_${gradeId}"placeholder="Nombre de nota" />
                            </div>
                            <div class="col-md-6">
                                <input type="text" class="form-control" name="group_${groupId}_grade_${gradeId}_percentage" placeholder="Porcentaje" />
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    grade(gradeId, groupId)
    {
        return `
            <div class="list-group-item">
                <div class="row">
                    <div class="col-md-6">
                        <input type="text" class="form-control" name="group_${groupId}_grade_${gradeId}"placeholder="Nombre de nota" />
                    </div>
                    <div class="col-md-6">
                        <input type="text" class="form-control" name="group_${groupId}_grade_${gradeId}_percentage" placeholder="Porcentaje" />
                    </div>
                </div>
            </div>
        `;
    }
}

const gradingStructure = new GradingStructure();
