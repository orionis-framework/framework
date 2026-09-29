from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(slots=True, kw_only=True, frozen=True)
class Argument:
    """
    Represent a function or method argument with type and resolution metadata.

    Parameters
    ----------
    name : str
        The name of the argument.
    resolved : bool
        Indicates whether the argument has been resolved or processed.
    module_name : str
        The module where the argument's type is defined.
    class_name : str
        The class representing the argument's type.
    type : type[Any]
        The Python type object for the argument's type.
    full_class_path : str
        The complete dotted path to the argument's type (module.class).
    is_keyword_only : bool, optional
        Indicates if the argument is keyword-only (default is False).
    is_schema : bool, optional
        Indicates if the argument is a schema (default is False).
    default : Any | None, optional
        The default value of the argument, if any (default is None).
    """

    # Required identification and type-resolution fields.
    name: str
    resolved: bool
    module_name: str
    class_name: str
    type: type[Any]
    full_class_path: str

    # Optional metadata fields with sensible defaults.
    is_keyword_only: bool = False
    is_schema: bool = False
    default: Any | None = None

    def __post_init__(self) -> None:
        """
        Validate field types after dataclass initialisation.

        Raises
        ------
        TypeError
            If ``module_name``, ``class_name``, or ``full_class_path`` is not a
            string.
        ValueError
            If ``type`` is ``None`` and no ``default`` value is provided.
        """
        if not isinstance(self.module_name, str):
            msg = (
                f"module_name must be a str, "
                f"got {type(self.module_name).__name__!r}"
            )
            raise TypeError(msg)
        if not isinstance(self.class_name, str):
            msg = (
                f"class_name must be a str, "
                f"got {type(self.class_name).__name__!r}"
            )
            raise TypeError(msg)
        if not isinstance(self.full_class_path, str):
            msg = (
                f"full_class_path must be a str, "
                f"got {type(self.full_class_path).__name__!r}"
            )
            raise TypeError(msg)
        if self.default is None and self.type is None:
            msg = "type must not be None when no default value is provided"
            raise ValueError(msg)
