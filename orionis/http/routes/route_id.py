"""Generate process-qualified identifiers for registered routes."""

import itertools
import os
import time

# Read the timestamp included in each route identifier.
_time_ns = time.time_ns

# Advance the process-local route sequence.
_next_id = itertools.count(1).__next__
"""Advance the process-local route sequence."""

# Include the process identifier in generated route identifiers.
_pid = str(os.getpid())
"""Include the process identifier in generated route identifiers."""

class RouteID:
    """Generate process-qualified identifiers for registered routes."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @staticmethod
    def next(method: str, path: str) -> str:
        """Generate a unique route identifier.

        Parameters
        ----------
        method : str
            HTTP method (e.g., GET, POST, PUT, DELETE).
        path : str
            Route path.

        Returns
        -------
        str
            Unique route identifier combining method, path, timestamp,
            and counter.
        """
        return f"{method}:{path}:{_pid}:{_time_ns()}:{_next_id()}"
