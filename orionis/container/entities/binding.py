from __future__ import annotations
from dataclasses import dataclass, field
from orionis.container.enums.lifetimes import Lifetime
from orionis.support.entities.base import BaseEntity

@dataclass(frozen=True, kw_only=True)
class Binding(BaseEntity):
    """
    Represent a binding between a contract and its implementation.

    Parameters
    ----------
    contract : type | None
        Contract of the concrete class to inject.
    concrete : type | None
        Concrete class implementing the contract.
    instance : object | None
        Concrete instance of the class, if provided.
    lifetime : Lifetime
        Lifetime of the instance.
    alias : str | None
        Alias for resolving the dependency from the container.

    Returns
    -------
    None
        This class does not return a value upon instantiation.
    """

    contract: type | None = field(
        default=None,
        metadata={
            "description": "Contract of the concrete class to inject.",
            "default": None,
        },
    )

    concrete: type | None = field(
        default=None,
        metadata={
            "description": "Concrete class implementing the contract.",
            "default": None,
        },
    )

    instance: object | None = field(
        default=None,
        metadata={
            "description": "Concrete instance of the class, if provided.",
            "default": None,
        },
    )

    lifetime: Lifetime = field(
        default=Lifetime.TRANSIENT,
        metadata={
            "description": "Lifetime of the instance.",
            "default": Lifetime.TRANSIENT,
        },
    )

    alias: str | None = field(
        default=None,
        metadata={
            "description": "Alias for resolving the dependency from the container.",
            "default": None,
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the type of the 'lifetime' attribute after initialization.

        Ensures that the 'lifetime' attribute is an instance of Lifetime.

        Parameters
        ----------
        self : Binding
            The instance of the Binding class.

        Returns
        -------
        None
            This method does not return a value.
        """
        # Ensure 'lifetime' is an instance of Lifetime
        if not isinstance(self.lifetime, Lifetime):
            error_msg = (
                "The 'lifetime' attribute must be an instance of 'Lifetime', but "
                f"received type '{type(self.lifetime).__name__}'."
            )
            raise TypeError(error_msg)
