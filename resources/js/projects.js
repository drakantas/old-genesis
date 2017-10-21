class Projects
{
    constructor()
    {
        this.reviewsList = $('#reviews_list');
        this.readReview = $('#read_review');
        this.pendingReviewsList = $('#pending_reviews_list');
        this.registerReview = $('#register_review');
        this.registerReviewEditor = 'review_body_editor';
        this.clickedReview = null;
        this.reviewers = null;
        this.decisionPanel = null;
        this.assignStuffRoute = null;

        this.editorConfig = {
            toolbar: [
                ['style', ['bold', 'italic', 'underline', 'clear']],
                ['font', ['strikethrough', 'superscript', 'subscript']],
                ['fontsize', ['fontsize']],
                ['color', ['color']],
                ['para', ['ul', 'ol', 'paragraph']],
                ['height', ['height']],
                ['insert', ['table', 'video', 'link', 'hr']]
            ],
            dialogsInBody: true,
            dialogsFade: true,
            disableDragAndDrop: true,
            placeholder: 'Escriba su observación aquí...',
            lang: 'es-ES'
        };

        this.registerEvents();
    }

    fetchReviewRoute(review, project = null, myOwn = true)
    {
        return  myOwn ? `/projects/my-project/review/${review}` : `/projects/${project}/review/${review}`;
    }

    atOwnProject()
    {
        path = document.location.pathname.split('/');

        return path[2] === 'my-project' ? true : path[2];
    }

    registerEvents()
    {
        let $this = this;

        $(this.reviewsList.find('tbody > tr')).on('click', (e) => {
            $this.getReview($(e.currentTarget), $this.handleReadReview);
            $this.readReview.modal();
        });

        $(this.pendingReviewsList.find('tbody > tr')).on('click', (e) => {
            $this.clickedReview = $(e.currentTarget);
            const modal_body = $($this.registerReview.find('.modal-body')[0]);
            modal_body.html($this.registerReviewContent());
            $(`#${$this.registerReviewEditor}`).summernote($this.editorConfig);
            $this.registerReview.modal();
        });

        $this.readReview.on('hidden.bs.modal', function (e) {
            const modal_body = $($this.readReview.find('.modal-body')[0]);
            modal_body.html($this.printError('Debes seleccionar una observación...', 'warning'));
        });

        $this.registerReview.on('hidden.bs.modal', function (e) {
            const modal_body = $($this.registerReview.find('.modal-body')[0]);
            modal_body.html($this.printError('Debes seleccionar una observación...', 'warning'));
        });

        $(document).on('click', 'button#submit_review', (e) => {
            let data = new FormData();
            data.append('body', $(`#${$this.registerReviewEditor}`).summernote('code'));

            if ($this.clickedReview !== null)
            {
                $this.postReview($this.clickedReview, data, {'Content-Type': 'application/x-www-form-urlencoded'},
                                 $this.handlePostReview);
            }
            else
            {
                const alert_wrapper = $(`.${$this.registerReviewEditor}_alert`);
                alert_wrapper.html($this.printError('Acabas de registrar esta observación, ya no puede ser modificada.', 'warning'));
            }
        });

        $('.assign_reviewer').on('click', (e) => {
            e.preventDefault();

            $this.assignStuffRoute = $(e.currentTarget).attr('href');

            $this.fetchReviewers((reviewers) => {
                const modalBody = $($('#assign_reviewer').find('.modal-body')[0]);
                modalBody.html($this.assignReviewerContent(reviewers));
                $(modalBody.find('#_reviewers')[0]).selectpicker();
                $('#assign_reviewer').modal();
            });
        });

        $('.assign_presentation_date').on('click', (e) => {
            e.preventDefault();

            $this.assignStuffRoute = $(e.currentTarget).attr('href');

            $this.fetchDecisionPanel((decision_panel) => {
                const modalBody = $($('#assign_presentation_date').find('.modal-body')[0]);
                modalBody.html($this.assignPresentationDateContent(decision_panel));
                $(modalBody.find('#_decision_panel')[0]).selectpicker();
                $('#presentation_datetimepicker').datetimepicker();
                $('#assign_presentation_date').modal();
            });
        });

        $(document).on('click', '.submit-btn', (e) => {
            const modal_body = $(e.currentTarget).parent().parent().parent();
            const alert_wrapper = $(modal_body.find('.alert_wrapper')[0]);

            if ($this.assignStuffRoute === null)
            {
                alert_wrapper.html($this.printError('Algo ha sucedido... Intentalo otra vez.', 'warning'));
                return;
            }

            const data = new FormData(modal_body.find('form')[0]);
            axios.post($this.assignStuffRoute, data, {'Content-Type': 'application/x-www-form-urlencoded'})
                 .then((response) => {
                    alert_wrapper.html($this.printError(response.data.message, 'success'));
                 })
                 .catch((error) => {
                    const response = error.response;

                    if (!(response.status === 400 || response.status === 401 || response.status === 404)) {
                        console.log(error);
                        return;
                    }
                    if (!Array.isArray(response.data.message))
                    {
                        alert_wrapper.html($this.printError(response.data.message));
                    }
                    else
                    {
                        let errors = '<ul>';
                        for (const _e of response.data.message)
                        {
                            errors = errors + `<li>${_e}</li>`;
                        }
                        errors = errors + '</ul>';
                        alert_wrapper.html($this.printError(errors));
                    }
                 });
        });

        $('#assign_reviewer, #assign_presentation_date').on('hidden.bs.modal', (e) => {
            $($(e.currentTarget).find('.modal-body')[0]).html('');
        });
    }



    handlePostReview($this, response)
    {
        const alert_wrapper = $(`.${$this.registerReviewEditor}_alert`);

        if (response.status === 400)
        {
            alert_wrapper.html($this.printError(response.data.message));
        }
        else if (response.status === 200)
        {
            alert_wrapper.html($this.printError(response.data.message, 'success'));
            $this.clickedReview.remove();
            $this.clickedReview = null;
        }

        return;
    }

    handleReadReview($this, response)
    {
        const modal_body = $($this.readReview.find('.modal-body')[0]);

        if (response.status === 401)
        {
            modal_body.html($this.printError('No autorizado para ver esta observación...'));
        }
        else if (response.status === 404)
        {
            modal_body.html($this.printError('Observación no encontrada...'));
        }
        else if (response.status === 412)
        {
            modal_body.html($this.printError(response.data.message, 'warning'));
        }
        else if (response.status === 200)
        {
            modal_body.html($this.readReviewContent(response.data));
        }

        return;
    }

    getReview(review, callback)
    {
        let $this = this,
            project = this.atOwnProject(),
            myOwn = true;

        if (project === true)
        {
            project = null;
        }
        else
        {
            myOwn = false;
        }

        axios.get($this.fetchReviewRoute(review.data('id'), project, myOwn))
             .then(function (response) {
                callback($this, response);
             })
             .catch(function (error) {
                callback($this, error.response);
             });
    }

    postReview(review, data, headers, callback)
    {
        let $this = this;

        axios.post(
            $this.fetchReviewRoute(review.data('id'), review.data('project'), false), data, headers)
             .then(function (response) {
                callback($this, response);
             })
             .catch(function (error) {
                callback($this, error.response);
             });
    }

    registerReviewContent()
    {
        return `
            <div class="${this.registerReviewEditor}_alert"></div>
            <form>
                <div id="${this.registerReviewEditor}"></div>
                <div class="text-right">
                    <button type="button" id="submit_review" class="btn btn-success">Registrar</button>
                </div>
            </form>
        `;
    }

    readReviewContent(data)
    {
        return `
            <em>Por, </em><a href="/profile/${data.author.id}">${data.author.nombres} ${data.author.apellidos}</a><br />
                ${data.author.rol}<br />
                <hr class="divider">
                ${data.contenido || ''}
        `;
    }

    printError(message, alert_type = 'danger')
    {
        return `<div class="alert alert-${alert_type}">${message}</div>`;
    }

    fetchReviewers(callback)
    {
        if (this.reviewers !== null)
        {
            return callback(this.reviewers);
        }

        let $this = this;

        axios.get('/reviewers')
             .then(function (response) {
                $this.reviewers = response.data;
                return callback($this.reviewers);
             })
             .catch(function (error) {
                const modalBody = $($('#assign_reviewer').find('.modal-body')[0]);
                modalBody.html(`<div class="alert alert-danger">${error.response.data.message}</div>`);
                $('#assign_reviewer').modal();
             });
    }

    fetchDecisionPanel(callback)
    {
        if (this.decisionPanel !== null)
        {
            return callback(this.decisionPanel);
        }

        let $this = this;

        axios.get('/decision-panel')
             .then(function (response) {
                $this.decisionPanel = response.data;
                return callback($this.decisionPanel);
             })
             .catch(function (error) {
                const modalBody = $($('#assign_presentation_date').find('.modal-body')[0]);
                modalBody.html(`<div class="alert alert-danger">${error.response.data.message}</div>`);
                $('#assign_presentation_date').modal();
             });
    }

    assignReviewerContent(reviewers)
    {
        let _reviewers = '';

        if (reviewers.length > 0)
        {
            for (const reviewer of reviewers)
            {
                _reviewers = _reviewers + `<option value="${reviewer.id}">${reviewer.nombres} ${reviewer.apellidos} - ${reviewer.rol}</option>`;
            }
        }

        return `
            <div class="alert_wrapper"></div>
            <form>
                <div class="form-group">
                    <label for="reviewers">Asignar a</label>
                    <select class="selectpicker" name="reviewers" id="_reviewers" data-live-search="true" data-width="100%" multiple>
                        ${_reviewers}
                    </select>
                </div>
                <div class="text-right">
                    <button type="button" class="btn btn-success submit-btn">Asignar</button>
                </div>
            </form>
        `;
    }

    assignPresentationDateContent(decisionPanel)
    {
        let _decisionPanel = '';

        if (decisionPanel.length > 0)
        {
            for (const dude of decisionPanel)
            {
                _decisionPanel = _decisionPanel + `<option value="${dude.id}">${dude.nombres} ${dude.apellidos} - ${dude.rol}</option>`;
            }
        }

        return `
            <div class="alert_wrapper"></div>
            <form>
                <div class="form-group">
                    <label for="_decision_panel">Jurado de sustentación</label>
                    <select class="selectpicker" name="decision_panel" id="_decision_panel" data-live-search="true" data-width="100%" multiple>
                        ${_decisionPanel}
                    </select>
                </div>
                <div class="form-group">
                    <label for="presentation_date">Fecha de sustentación</label>
                    <div class="input-group date" id="presentation_datetimepicker">
                        <input type="text" name="presentation_date" id="presentation_date" class="form-control" />
                        <span class="input-group-addon">
                            <span class="glyphicon glyphicon-calendar"></span>
                        </span>
                    </div>
                </div>
                <div class="text-right">
                    <button type="button" class="btn btn-success submit-btn">Asignar</button>
                </div>
            </form>
        `;
    }
}

const projects = new Projects();
