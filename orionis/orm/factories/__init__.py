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

_EXPORTS = {
    "Factory": ("orionis.orm.factories.factory", "Factory"),
    "FactoryConcurrencyException": ("orionis.orm.factories.exceptions", "FactoryConcurrencyException"),
    "FactoryConfigurationException": ("orionis.orm.factories.exceptions", "FactoryConfigurationException"),
    "FactoryDefinitionException": ("orionis.orm.factories.exceptions", "FactoryDefinitionException"),
    "FactoryDependencyException": ("orionis.orm.factories.exceptions", "FactoryDependencyException"),
    "FactoryException": ("orionis.orm.factories.exceptions", "FactoryException"),
    "FactoryPersistenceException": ("orionis.orm.factories.exceptions", "FactoryPersistenceException"),
    "Fake": ("orionis.orm.factories.fake", "Fake"),
    "OptionalFake": ("orionis.orm.factories.fake", "OptionalFake"),
    "Sequence": ("orionis.orm.factories.sequence", "Sequence"),
    "UniqueFake": ("orionis.orm.factories.fake", "UniqueFake"),
}

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
