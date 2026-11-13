"""Define available kernel types in the system."""

from enum import Enum, auto


class KernelContext(Enum):
    """
    Define available kernel types in the system.

    Attributes
    ----------
    CONSOLE : orionis.failure.enums.KernelContext
        Kernel for command-line or console execution.
    HTTP : orionis.failure.enums.KernelContext
        Kernel for HTTP environments, such as web servers.

    Returns
    -------
    orionis.failure.enums.KernelContext
        An instance of the KernelContext enumeration.
    """

    # Kernel for command-line or console execution
    CONSOLE = auto()

    # Kernel for HTTP environments, such as web servers
    HTTP = auto()
