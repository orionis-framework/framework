from enum import Enum

class SQLiteJournalMode(Enum):
    """
    Enumerate SQLite journal modes.

    SQLite uses various journal modes to manage transaction logging and
    database integrity. Each mode balances performance, durability, and
    concurrency differently.

    Attributes
    ----------
    DELETE : str
        The journal file is deleted at the end of each transaction.
    TRUNCATE : str
        The journal file is truncated to zero bytes instead of being deleted.
    PERSIST : str
        The journal file is retained but marked as inactive after a transaction.
    MEMORY : str
        The journal is kept in volatile memory, offering faster performance but
        less safety.
    WAL : str
        Write-Ahead Logging mode, which can improve concurrency and performance.
    OFF : str
        Disables journaling entirely, providing no protection against failures.

    Returns
    -------
    None
        This class defines enumeration members and does not return a value.
    """

    DELETE = "DELETE"      # Default: journal file deleted at transaction end.
    TRUNCATE = "TRUNCATE"  # Journal file truncated to zero bytes.
    PERSIST = "PERSIST"    # Journal file retained but marked inactive.
    MEMORY = "MEMORY"      # Journal kept in memory (faster, less safe).
    WAL = "WAL"            # Write-Ahead Logging for improved concurrency.
    OFF = "OFF"            # Journaling disabled (no failure protection).
