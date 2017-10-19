class Projects
{
    constructor()
    {
        this.reviewsList = $('#reviews_list');
        this.readReview = $('#read_review');

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
            console.log('wat');
            $this.readReview.modal();
        });
    }

    handleReadReview($this, response)
    {
        const modal_body = $($this.readReview.find('.modal-body')[0]);

        if (response.status == 401)
        {
            modal_body.html($this.printError('No autorizado para ver esta observación...'));
            return;
        }

        if (response.status == 404)
        {
            modal_body.html($this.printError('Observación no encontrada...'));
            return;
        }

        if (response.status == 412)
        {
            modal_body.html($this.printError(response.data.message, 'warning'));
            return;
        }

        if (response.status == 200)
        {
            modal_body.html($this.readReviewContent(response.data));
            return;
        }
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
