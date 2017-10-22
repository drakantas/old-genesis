// Definir jQuery globalmente
window.$ = window.jQuery = require('jquery');

// Axios
window.axios = require('axios');

// Incluir Bootstrap
require('bootstrap-sass');

// Moment.js
require('moment');

// Bootstrap plugins
require('eonasdan-bootstrap-datetimepicker');
require('bootstrap-select');
require('metismenu');
require('summernote');
require('summernote/lang/summernote-es-ES');

require('../js/main_menu')
require('../js/school_term');
require('../js/attendance');
require('../js/grades');
require('../js/projects');
require('../js/grading_structure');
