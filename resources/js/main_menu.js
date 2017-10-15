class MainMenu
{
    /*
     * TODO
     * -----
     * Registrar en la BD el estado en el cual se encuentra una sección.
     * Referencia: http://mm.onokumus.com/mm-event.html
     */
    constructor()
    {
        const pathPattern = '\\/([a-zA-Z0-9\\-]+)';
        this.uriPathReg = new RegExp(pathPattern, 'g');

        this.selector = $('.app_nav');

        this.config = {
            toggle: false
        };

        this.schoolTermSelector = $('#school_term_selector');

        this.registerHandler();
        this.registerSchoolTermSelectorHandler();
    }

    getPaths()
    {
        const path = document.location.pathname;
        let paths = [];

        while (_path = this.uriPathReg.exec(path)) {
            paths.push(_path[1]);
        }

        return paths;
    }

    registerHandler()
    {
        this.selector.metisMenu(this.config);
    }

    registerSchoolTermSelectorHandler()
    {
        let $this = this;
        this.schoolTermSelector.on('changed.bs.select', (e, clickedIndex, newValue, oldValue) => {
            const paths = $this.getPaths();

            if (paths.length > 0)
            {
                const schoolTermId = $($(e.currentTarget).find('option')[clickedIndex]).val();
                if (paths[paths.length - 1].startsWith('school-term'))
                {
                    document.location = document.location.href.replace(paths[paths.length - 1], `school-term-${schoolTermId}`);
                }
                else
                {
                    document.location = document.location + `/school-term-${schoolTermId}`;
                }
            }
        });
    }
}

const mainMenu = new MainMenu();
