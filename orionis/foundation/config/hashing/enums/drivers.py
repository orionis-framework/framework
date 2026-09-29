from enum import StrEnum

class Drivers(StrEnum):
    """
    Enumerate supported password hashing drivers.

    Attributes
    ----------
    ARGON2 : str
        Represents the Argon2id password hashing driver.
    BCRYPT : str
        Represents the bcrypt password hashing driver.

    Returns
    -------
    Drivers
        An enumeration member representing a hashing driver.
    """

    ARGON2 = "argon2"
    BCRYPT = "bcrypt"
