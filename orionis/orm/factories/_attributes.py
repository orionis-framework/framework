from copy import deepcopy
from inspect import iscoroutine
from types import NoneType
from typing import Any
from orionis.orm.factories.exceptions import FactoryDefinitionException

_ATOMIC_TYPES = frozenset({NoneType, bool, bytes, complex, float, int, str})

def copy_attributes(value: object, source: str) -> dict[str, Any]:
    """
    Validate and detach attributes from caller-owned mutable data.

    Parameters
    ----------
    value : object
        Candidate dictionary of model attributes.
    source : str
        Origin used in validation errors.

    Returns
    -------
    dict of str to Any
        Independent attributes, including nested containers.

    Raises
    ------
    FactoryDefinitionException
        If the value is not a dictionary with string keys.
    """
    if type(value) is dict:
        atomic = True
        for key, item in value.items():
            if not isinstance(key, str):
                error_msg = f"{source} must return a dictionary with string keys."
                raise FactoryDefinitionException(error_msg)
            atomic = atomic and type(key) is str and type(item) in _ATOMIC_TYPES
        return value.copy() if atomic else deepcopy(value)
    if iscoroutine(value):
        value.close()
    if not isinstance(value, dict) or any(
        not isinstance(key, str) for key in value
    ):
        error_msg = f"{source} must return a dictionary with string keys."
        raise FactoryDefinitionException(error_msg)
    return deepcopy(value)
