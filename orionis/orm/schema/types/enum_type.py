from __future__ import annotations
from orionis.orm.schema.column.definition import ColumnDefinition
from orionis.orm.schema.column.options import ColumnOptions
from orionis.orm.schema.types.column_type import ColumnType

class Enum(ColumnDefinition):
    """String-backed enumeration column."""

    __slots__ = ()

    def __init__(
        self,
        *enums: str,
        name: str | None = None,
        create_constraint: bool = False,
        native_enum: bool = True,
        length: int | None = None,
        validate_strings: bool = False,
    ) -> None:
        """
        Construct an enum.

        Parameters
        ----------
        *enums : str
            Allowed string values, at least one is required.
        name : str or None, optional
            Name of the enumerated database type.
        create_constraint : bool, optional
            When emulating a non-native enum, also build a CHECK
            constraint against the allowed values.
        native_enum : bool, optional
            Whether to use the backend's native ``ENUM`` type.
        length : int or None, optional
            Custom ``VARCHAR`` length for non-native enumerations.
        validate_strings : bool, optional
            Whether to validate string literals against allowed values.

        Returns
        -------
        None
            This method does not return a value.

        Raises
        ------
        ValueError
            If no values are provided or any value is not a string.
        """
        # Enum columns are meaningless without at least one allowed value.
        if not enums or any(not isinstance(v, str) or not v for v in enums):
            error_msg = "Enum requires at least one non-empty string value."
            raise ValueError(error_msg)
        super().__init__(
            ColumnType.ENUM,
            ColumnOptions(
                enum_values=tuple(enums),
                enum_name=name,
                create_constraint=create_constraint,
                native_enum=native_enum,
                length=length,
                validate_strings=validate_strings,
            ),
        )
