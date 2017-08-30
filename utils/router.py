from inspect import ismodule
from typing import Dict, Generator, Tuple, List, Union

from aiohttp.web import Application


class Router:
    def __init__(self, app_: Application):
        self.map_attr = 'routes'
        self.app = app_
        self.routes = dict()

    def update(self, modules_: Union[Tuple, List]):
        for m in modules_:
            self._register_module(m)

    def register(self):
        for route, view in self.routes.items():
            self.app.router.add_route('*', route, view)

    def _get_map(self, module_) -> Dict:
        try:
            _map = getattr(module_, self.map_attr)

            if not isinstance(_map, dict):
                raise ValueError('El atributo <{}> del módulo <{}> tiene que ser un '
                                 'diccionario'.format(self.map_attr,  module_.__name__))
        except AttributeError:
            raise AttributeError('No se encontró el atributo <{}> en el módulo <{}>'.format(self.map_attr,
                                                                                            module_.__name__))
        else:
            return _map

    def _get_routes(self, routes: dict, *groups) -> Generator:
        for path, v in routes.items():
            if not isinstance(v, dict):
                path = ('/' + path if path[:1] != '/' else path) if not groups else self._prepend_path('/'.join(groups),
                                                                                                       path)
                yield path, v
            else:
                yield from self._get_routes(v, *groups, *(path,))

    def _register_module(self, module_):
        if not ismodule(module_):
            raise TypeError('El objeto <{}> no es un módulo'.format(module_.__name__))

        self.routes.update(self._get_routes(dict(self._get_map(module_))))

    @staticmethod
    def _prepend_path(prep_path: str, path: str) -> str:
        full_path = '/{0}/{1}' if path[:1] != '/' else '/{0}{1}'

        return full_path.format(prep_path, path)
