from collections.abc import Callable
from copy import deepcopy
from inspect import iscoroutinefunction
from typing import Any
from orionis.orm.factories._attributes import copy_attributes
from orionis.orm.factories.exceptions import (
    FactoryConfigurationException,
    FactoryDefinitionException,
)

type SequenceEntry = dict[str, Any] | Callable[[int], dict[str, Any]]

class Sequence:
    """
    Describe cycling attributes without owning a shared counter.

    Callable entries receive the factory's absolute, zero-based index.
    Every factory owns its position, even when sharing this specification.
    """

    __slots__ = ("_entries",)

    def __init__(self, *entries: SequenceEntry) -> None:
        """Capture one or more detached dictionaries or index callbacks.

        Parameters
        ----------
        *entries : dict or Callable
            Entries to cycle through in their supplied order.

        Raises
        ------
        FactoryConfigurationException
            If no entries or an asynchronous callback is supplied.

        Returns
        -------
        None
            Apply the described operation.
        """
        if not entries:
            error_msg = "A sequence requires at least one entry."
            raise FactoryConfigurationException(error_msg)
        validated: list[SequenceEntry] = []
        for entry in entries:
            is_callback = callable(entry)
            if iscoroutinefunction(entry) or (
                is_callback and iscoroutinefunction(entry.__call__)
            ):
                error_msg = "Sequence callbacks must be synchronous."
                raise FactoryConfigurationException(error_msg)
            try:
                validated.append(
                    entry if is_callback
                    else copy_attributes(entry, "Sequence"),
                )
            except FactoryDefinitionException as exc:
                error_msg = "Sequence entries must be dictionaries or callbacks."
                raise FactoryConfigurationException(error_msg) from exc
        self._entries = tuple(validated)

    def resolve(self, index: int) -> dict[str, Any]:
        """
        Resolve attributes for a factory-owned sequence position.

        Parameters
        ----------
        index : int
            Nonnegative absolute index supplied by the factory.

        Returns
        -------
        dict of str to Any
            Detached attributes for this position.

        Raises
        ------
        FactoryConfigurationException
            If the index is not a nonnegative integer.
        """
        if isinstance(index, bool) or not isinstance(index, int) or index < 0:
            error_msg = "A sequence index must be a nonnegative integer."
            raise FactoryConfigurationException(error_msg)
        entry = self._entries[index % len(self._entries)]
        if callable(entry):
            return copy_attributes(entry(index), "Sequence")
        return deepcopy(entry)
