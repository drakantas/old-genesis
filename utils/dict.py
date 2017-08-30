from typing import Union, Tuple, List, Generator


class PointNestedDict(dict):
    def __init__(self, *args):
        pass

    def _nest(le_dict: dict, inner_dict_parents: Union[Tuple, List] = None) -> dict:
        def _nest_dict(_dict: dict, parents: Union[Tuple, List] = None) -> Generator:
            for k, v in _dict.items():
                if not isinstance(_dict[k], dict):
                    yield k if not parents else '.'.join(parents + [k]), v
                else:
                    yield from _nest_dict(_dict[k], (k,) if not parents else list(parents) + [k])
        return dict(_nest_dict(le_dict, inner_dict_parents))
