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
        this.selector = $('.app_nav');

        this.config = {
            toggle: false
        };

        this.registerHandler();
    }

    registerHandler()
    {
        this.selector.metisMenu(this.config);
    }
}

const mainMenu = new MainMenu();
