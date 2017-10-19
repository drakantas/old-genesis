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
}

const projects = new Projects();
