from enum import Enum, auto

class KernelContext(Enum):
    """
    Define available kernel types in the system.

    Attributes
    ----------
    CONSOLE : KernelContext
        Kernel for command-line or console execution.
    HTTP : KernelContext
        Kernel for HTTP environments, such as web servers.

    Returns
    -------
    KernelContext
        An instance of the KernelContext enumeration.
    """

    # Kernel for command-line or console execution
    CONSOLE = auto()

    # Kernel for HTTP environments, such as web servers
    HTTP = auto()
