from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.filesystems.entitites.disks import Disks
from orionis.foundation.config.filesystems.enums.disk_name import DiskName
from orionis.environment.facade import Env
from orionis.support.entities.base import BaseEntity

# Pre-computed frozenset of valid disk names for O(1) membership checks
_DISK_NAMES: frozenset[str] = frozenset(DiskName._member_names_)

@dataclass(frozen=True, kw_only=True)
class Filesystems(BaseEntity):
    """
    Represent the filesystems configuration.

    Attributes
    ----------
    default : DiskName | str
        The name of the default filesystem disk to use. Accepts a
        ``DiskName`` enum member or a plain string (e.g. ``'local'``).
    disks : Disks | dict
        A collection of available filesystem disks.
    """

    default: DiskName | str = field(
        default_factory=lambda: Env.get("FILESYSTEM_DISK", DiskName.LOCAL.value),
        metadata={
            "description": (
                "The default filesystem disk name. Can be a member of the "
                "DiskName enum or a string (e.g., 'local', 's3')."
            ),
            "default": DiskName.LOCAL.value,
        },
    )

    disks: Disks | dict = field(
        default_factory=Disks,
        metadata={
            "description": "A collection of available filesystem disks.",
            "default": lambda: Disks().toDict(),
        },
    )

    def __post_init__(self) -> None:
        """
        Validate the types of attributes after initialization.

        Parameters
        ----------
        self : Filesystems
            The instance of the Filesystems class.

        Returns
        -------
        None
            This method does not return a value.
        """
        super().__post_init__()

        # Reject types that are neither DiskName enum nor string
        if not isinstance(self.default, (DiskName, str)):
            error_msg = (
                "The 'default' attribute must be an instance of "
                "DiskName or a string."
            )
            raise TypeError(error_msg)

        # Validate string disk names and normalise to canonical enum value
        if isinstance(self.default, str):
            _value = self.default.upper().strip()
            if _value not in _DISK_NAMES:
                error_msg = (
                    "The 'default' attribute must be one of "
                    f"{sorted(m.value for m in DiskName)!s}."
                )
                raise ValueError(error_msg)
            # Normalise to the canonical string value stored in the enum
            object.__setattr__(self, "default", DiskName[_value].value)
        else:
            # Extract the raw string value from the DiskName enum member
            object.__setattr__(self, "default", self.default.value)

        # Ensure 'disks' is either a Disks instance or a dictionary.
        if not isinstance(self.disks, (Disks, dict)):
            error_msg = (
                "The 'disks' property must be an instance of Disks or a dictionary."
            )
            raise TypeError(error_msg)
        # Convert dict to Disks instance if necessary.
        if isinstance(self.disks, dict):
            object.__setattr__(self, "disks", Disks(**self.disks))
