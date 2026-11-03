"""Define ANSI escape codes for styling terminal text and backgrounds."""

from enum import Enum

class ANSIColors(Enum):
    """
    Define ANSI escape codes for styling terminal text and backgrounds.

    This Enum provides ANSI escape codes for foreground and background colors,
    as well as text styles such as bold, underline, dim, italic, and magenta.
    Use these codes to enhance console output readability and emphasis.

    Returns
    -------
    str
        The ANSI escape code string for the selected color or style.
    """

    # Reset all colors and styles to default
    DEFAULT = "\033[0m"
    """Reset all colors and styles to default."""

    # Background color for informational messages
    BG_INFO = "\033[44m"
    """Background color for informational messages."""

    # Background color for error messages
    BG_ERROR = "\033[41m"
    """Background color for error messages."""

    # Background color for failure messages
    BG_FAIL = "\033[48;5;166m"
    """Background color for failure messages."""

    # Background color for warning messages
    BG_WARNING = "\033[43m"
    """Background color for warning messages."""

    # Background color for success messages
    BG_SUCCESS = "\033[42m"
    """Background color for success messages."""

    # Foreground color for informational messages
    TEXT_INFO = "\033[34m"
    """Foreground color for informational messages."""

    # Foreground color for error messages
    TEXT_ERROR = "\033[91m"
    """Foreground color for error messages."""

    # Foreground color for warning messages
    TEXT_WARNING = "\033[33m"
    """Foreground color for warning messages."""

    # Foreground color for success messages
    TEXT_SUCCESS = "\033[32m"
    """Foreground color for success messages."""

    # Foreground color for white text
    TEXT_WHITE = "\033[97m"
    """Foreground color for white text."""

    # Foreground color for muted (gray) text
    TEXT_MUTED = "\033[90m"
    """Foreground color for muted (gray) text."""

    # Bold foreground color for informational messages
    TEXT_BOLD_INFO = "\033[1;34m"
    """Bold foreground color for informational messages."""

    # Bold foreground color for error messages
    TEXT_BOLD_ERROR = "\033[1;91m"
    """Bold foreground color for error messages."""

    # Bold foreground color for warning messages
    TEXT_BOLD_WARNING = "\033[1;33m"
    """Bold foreground color for warning messages."""

    # Bold foreground color for success messages
    TEXT_BOLD_SUCCESS = "\033[1;32m"
    """Bold foreground color for success messages."""

    # Bold foreground color for white text
    TEXT_BOLD_WHITE = "\033[1;97m"
    """Bold foreground color for white text."""

    # Bold foreground color for muted (gray) text
    TEXT_BOLD_MUTED = "\033[1;90m"
    """Bold foreground color for muted (gray) text."""

    # Bold text style
    TEXT_BOLD = "\033[1m"
    """Bold text style."""

    # Underlined text style
    TEXT_STYLE_UNDERLINE = "\033[4m"
    """Underlined text style."""

    # Foreground color for cyan text
    CYAN = "\033[36m"
    """Foreground color for cyan text."""

    # Dimmed foreground text style
    DIM = "\033[2m"
    """Dimmed foreground text style."""

    # Foreground color for magenta text
    MAGENTA = "\033[35m"
    """Foreground color for magenta text."""

    # Italicized foreground text style
    ITALIC = "\033[3m"
    """Italicized foreground text style."""
