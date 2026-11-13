"""Group the orm factories components and public imports."""

from typing import TYPE_CHECKING as _TYPE_CHECKING
from orionis._exports import resolve_export as _resolve_export

if _TYPE_CHECKING:
    from orionis.orm.factories.exceptions import (
        FactoryConcurrencyException,
        FactoryConfigurationException,
        FactoryDefinitionException,
        FactoryDependencyException,
        FactoryException,
        FactoryPersistenceException,
    )
    from orionis.orm.factories.factory import Factory
    from orionis.orm.factories.fake import Fake, OptionalFake, UniqueFake
    from orionis.orm.factories.sequence import Sequence

__all__ = [
    "Factory",
    "FactoryConcurrencyException",
    "FactoryConfigurationException",
    "FactoryDefinitionException",
    "FactoryDependencyException",
    "FactoryException",
    "FactoryPersistenceException",
    "Fake",
    "OptionalFake",
    "Sequence",
    "UniqueFake",
]

_EXCEPTIONS_MODULE = "orionis.orm.factories.exceptions"
"""Defining module shared by public factory exception exports."""
_FAKE_MODULE = "orionis.orm.factories.fake"
"""Defining module shared by public fake-data view exports."""

_EXPORTS = {
    "Factory": ("orionis.orm.factories.factory", "Factory"),
    "FactoryConcurrencyException": (_EXCEPTIONS_MODULE, "FactoryConcurrencyException"),
    "FactoryConfigurationException": (
        _EXCEPTIONS_MODULE,
        "FactoryConfigurationException",
    ),
    "FactoryDefinitionException": (_EXCEPTIONS_MODULE, "FactoryDefinitionException"),
    "FactoryDependencyException": (_EXCEPTIONS_MODULE, "FactoryDependencyException"),
    "FactoryException": (_EXCEPTIONS_MODULE, "FactoryException"),
    "FactoryPersistenceException": (_EXCEPTIONS_MODULE, "FactoryPersistenceException"),
    "Fake": (_FAKE_MODULE, "Fake"),
    "OptionalFake": (_FAKE_MODULE, "OptionalFake"),
    "Sequence": ("orionis.orm.factories.sequence", "Sequence"),
    "UniqueFake": (_FAKE_MODULE, "UniqueFake"),
}
"""Public export names mapped to their defining modules and attributes."""


def __getattr__(name: str) -> object:
    """
    Resolve and cache a public package export.

    Parameters
    ----------
    name : str
        Public attribute requested from this package.

    Returns
    -------
    object
        Exported object from its defining module.

    Raises
    ------
    AttributeError
        If the requested attribute is not exported.
    """
    return _resolve_export(globals(), _EXPORTS, name)


def __dir__() -> list[str]:
    """
    List loaded attributes and declared public exports.

    Returns
    -------
    list[str]
        Sorted attribute names available on this package.
    """
    return sorted(globals().keys() | _EXPORTS.keys())
