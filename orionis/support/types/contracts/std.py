from abc import ABC, abstractmethod

class IStdClass(ABC):

    __slots__ = ()

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
            This method does not return a value. Attributes are updated in-place.

        Raises
        ------
        OrionisStdValueException
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
            This method does not return a value. Attributes are removed in-place.

        Raises
        ------
        AttributeError
            If any of the specified attributes do not exist.
        """
