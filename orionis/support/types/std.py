from orionis.support.types.contracts.std import IStdClass

_DUNDER = "__"

class StdClass(IStdClass):

    RESERVED: frozenset

    @classmethod
    def __init_subclass__(cls, **kwargs: object) -> None:
        """
        Rebuild the reserved-names set for every subclass.

        Parameters
        ----------
        **kwargs : object
            Keyword arguments forwarded to the parent hook.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        super().__init_subclass__(**kwargs)
        cls.RESERVED = (
            frozenset(k for c in cls.__mro__ for k in vars(c)) | {"RESERVED"}
        )

    def __hash__(self) -> int:
        """
        Compute the hash value of the object based on its attributes.

        Returns
        -------
        int
            Hash value computed from the object's attributes.
        """
        # Combine attribute hashes independently of their order.
        h = 0
        for item in self.__dict__.items():
            h ^= hash(item)
        return h

    def __init__(self, **kwargs: object) -> None:
        """
        Initialize attributes from keyword arguments.

        Parameters
        ----------
        **kwargs : object
            Arbitrary keyword arguments to set as attributes.

        Returns
        -------
        None
            This method does not return a value. The object is initialized in-place.
        """
        # Skip dispatch entirely when no arguments are provided (cold path)
        if kwargs:
            self.update(**kwargs)

    def __repr__(self) -> str:
        """
        Return an unambiguous string representation for debugging.

        Returns
        -------
        str
            String representation of the object with its attributes.
        """
        # Include the concrete class name and its attributes.
        return f"{type(self).__name__}({self.__dict__})"

    def __str__(self) -> str:
        """
        Return a readable string representation of the object.

        Returns
        -------
        str
            String showing the object's attributes.
        """
        # Show attributes as a string
        return str(self.__dict__)

    def __eq__(self, other: object) -> bool:
        """
        Compare this object with another for attribute equality.

        Parameters
        ----------
        other : object
            Object to compare with.

        Returns
        -------
        bool
            True if both objects have the same attributes and values, otherwise False.
        """
        # Require both values to have the same concrete class.
        if type(other) is not type(self):
            return False
        return self.__dict__ == other.__dict__

    def toDict(self) -> dict:
        """
        Convert the object's attributes to a dictionary.

        Returns
        -------
        dict
            A shallow copy of the object's attributes.
        """
        # Return a copy to avoid external modifications
        return self.__dict__.copy()

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
        ValueError
            If an attribute name is reserved or conflicts with a class method.
        """
        reserved = type(self).RESERVED
        d = self.__dict__
        for key, value in kwargs.items():
            if key.startswith(_DUNDER) and key.endswith(_DUNDER):
                msg = f"Cannot set attribute with reserved name: {key}"
                raise ValueError(msg)
            # Reject names reserved by the object protocol.
            if key in reserved:
                msg = (
                    f"Cannot set attribute '{key}'"
                    " as it conflicts with a class method"
                )
                raise ValueError(msg)
            # Direct __dict__ write bypasses descriptor dispatch
            d[key] = value

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
        d = self.__dict__
        for attr in attributes:
            # Remove each present attribute from the instance dictionary.
            try:
                del d[attr]
            except KeyError as exc:
                msg = f"Attribute '{attr}' not found"
                raise AttributeError(msg) from exc

    @classmethod
    def fromDict(cls, dictionary: dict) -> StdClass:
        """
        Create a StdClass instance from a dictionary.

        Parameters
        ----------
        dictionary : dict
            Dictionary containing attribute names and values.

        Returns
        -------
        StdClass
            A new StdClass instance with attributes set from the dictionary.
        """
        # Allocate the instance without routing values through keyword arguments.
        reserved = cls.RESERVED
        obj = cls.__new__(cls)
        obj_dict = obj.__dict__
        for key, value in dictionary.items():
            if key.startswith(_DUNDER) and key.endswith(_DUNDER):
                msg = f"Cannot set attribute with reserved name: {key}"
                raise ValueError(msg)
            if key in reserved:
                msg = (
                    f"Cannot set attribute '{key}'"
                    " as it conflicts with a class method"
                )
                raise ValueError(msg)
            obj_dict[key] = value
        return obj


# Build the reserved-names frozenset from the complete MRO.
# Must be evaluated after the class body is fully defined.
StdClass.RESERVED = (
    frozenset(k for c in StdClass.__mro__ for k in vars(c)) | {"RESERVED"}
)
