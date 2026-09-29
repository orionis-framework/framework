from enum import Enum

class VerbosityMode(Enum):
    """
    Enumerate verbosity levels for test output.

    Attributes
    ----------
    SILENT : int
        No output will be shown.
    MINIMAL : int
        Minimal output will be displayed.
    DETAILED : int
        Detailed output will be provided (default).

    Returns
    -------
    VerbosityMode
        The selected verbosity level as an enumeration member.
    """

    SILENT = 0  # 0: Silent mode, no output
    MINIMAL = 1  # 1: Minimal output mode
    DETAILED = 2  # 2: Detailed output mode (default)
