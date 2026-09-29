from enum import Enum

class ArgumentAction(Enum):
    """
    Define valid action types for use with Python's argparse module.

    Each member represents a specific way argparse processes and stores argument
    values.

    Attributes
    ----------
    STORE : str
        Store the argument value directly.
    STORE_CONST : str
        Store a constant value when the argument is specified.
    STORE_TRUE : str
        Store True when the argument is specified.
    STORE_FALSE : str
        Store False when the argument is specified.
    APPEND : str
        Append each argument value to a list.
    APPEND_CONST : str
        Append a constant value to a list when the argument is specified.
    COUNT : str
        Count the number of times the argument is specified.
    HELP : str
        Display the help message and exit.
    VERSION : str
        Display version information and exit.

    Returns
    -------
    str
        The string value representing the corresponding argparse action type.
    """

    # Store the argument value directly
    STORE = "store"

    # Store a constant value when the argument is specified
    STORE_CONST = "store_const"

    # Store True when the argument is specified
    STORE_TRUE = "store_true"

    # Store False when the argument is specified
    STORE_FALSE = "store_false"

    # Append each argument value to a list
    APPEND = "append"

    # Append a constant value to a list when the argument is specified
    APPEND_CONST = "append_const"

    # Count the number of times the argument is specified
    COUNT = "count"

    # Display the help message and exit the program
    HELP = "help"

    # Display version information and exit the program
    VERSION = "version"
