from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.environment.enums.value_type import EnvironmentValueType

class IEnvironmentCaster(ABC):

    __slots__ = ()

    @abstractmethod
    def get(
        self,
    ) -> object:
        """
        Return the processed value according to the type hint.

        If a valid type hint is present, dispatch to the corresponding internal
        parsing method for that type. Supported type hints include: 'path', 'str',
        'int', 'float', 'bool', 'list', 'dict', 'tuple', 'set', and 'base64'.
        If no type hint is set, return the raw value.

        Parameters
        ----------
        self : EnvironmentCaster
            Instance of the EnvironmentCaster class.

        Returns
        -------
        object
            The value converted or processed according to the specified type hint.
            If no type hint is set, returns the raw value.

        Raises
        ------
        ValueError
            If an error occurs during type conversion or processing.
        TypeError
            If an error occurs during type conversion or processing.
        """

    @abstractmethod
    def to(
        self,
        type_hint: str | EnvironmentValueType,
    ) -> str:
        """
        Convert the internal value to the specified type and return as a string.

        Parameters
        ----------
        type_hint : str or EnvironmentValueType
            The type to which the internal value should be converted. Must be a
            valid option in `OPTIONS`.

        Returns
        -------
        str
            String representation of the value with the type hint prefix, e.g.,
            int:42, list:[1, 2, 3], etc.

        Raises
        ------
        ValueError
            If the provided type hint is invalid or conversion fails.
        """
