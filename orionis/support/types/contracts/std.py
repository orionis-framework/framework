"""Define the contract for std class implementations."""

from abc import ABC, abstractmethod


class IStdClass(ABC):
    """Define the contract for std class implementations."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    def toDict(self) -> dict:
        """
        Convert the object's attributes to a dictionary.

        Returns
        -------
        dict
            A shallow copy of the object's attributes.
        """

    @abstractmethod
    def update(self, **kwargs: object) -> None:
        """
        Update the object's attributes dynamically.

        Parameters
        ----------
        **kwargs : object
            Key-value pairs to update or add as attributes.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            If an attribute name is reserved or conflicts with a class method.
        """

    @abstractmethod
    def remove(self, *attributes: str) -> None:
        """
        Remove one or more attributes from the object.

        Parameters
        ----------
        *attributes : str
            Names of the attributes to remove.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        AttributeError
            If any of the specified attributes do not exist.
        """
