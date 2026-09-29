from enum import Enum

class EnvironmentValueType(Enum):
    """
    Define supported types for casting environment variable values.

    Attributes
    ----------
    BASE64 : str
        Base64 encoded value type.
    PATH : str
        File system path type.
    STR : str
        String value type.
    INT : str
        Integer value type.
    FLOAT : str
        Floating-point value type.
    BOOL : str
        Boolean value type.
    LIST : str
        List value type.
    DICT : str
        Dictionary value type.
    TUPLE : str
        Tuple value type.
    SET : str
        Set value type.
    """

    # Base64 encoded type
    BASE64 = "base64"

    # File system path type
    PATH = "path"

    # String type
    STR = "str"

    # Integer type
    INT = "int"

    # Floating-point type
    FLOAT = "float"

    # Boolean type
    BOOL = "bool"

    # List type
    LIST = "list"

    # Dictionary type
    DICT = "dict"

    # Tuple type
    TUPLE = "tuple"

    # Set type
    SET = "set"
