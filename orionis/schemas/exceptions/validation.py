# ruff: noqa: TC001
# Preserve the failure entity annotation for runtime constructor inspection.
"""Carry structured schema-validation failures."""

from __future__ import annotations
from collections.abc import Sequence
from orionis.schemas.entities.failure import ValidationFailure

# Fallback used when the exception is built without any failure.
_DEFAULT_MESSAGE = "The given data was invalid."
"""Fallback used when the exception is built without any failure."""


class ValidationException(Exception):
    """Carry structured schema-validation failures."""

    def __init__(
        self,
        failures: ValidationFailure | Sequence[ValidationFailure],
        message: str | None = None,
    ) -> None:
        """
        Initialize field errors and a summary from validation failures.

        Parameters
        ----------
        failures : ValidationFailure or collections.abc.Sequence[ValidationFailure]
            Single failure or collected payload failures in reporting order.
        message : str | None, optional
            Override the summary message reported to the client.

        Returns
        -------
        None
            No return value.
        """
        # Preserve order for every declared sequence implementation.
        collected: tuple[ValidationFailure, ...] = (
            tuple(failures) if isinstance(failures, Sequence) else (failures,)
        )

        # Preserve the public rule code alongside every field message.
        errors: dict[str, list[dict[str, str]]] = {}
        for failure in collected:
            detail = {"rule": failure.rule, "message": failure.message}
            bucket = errors.get(failure.field)
            if bucket is None:
                errors[failure.field] = [detail]
            else:
                bucket.append(detail)

        self.failures = collected
        """Single failure or collected payload failures in reporting order."""
        self.failure = collected[0] if collected else None
        """Failure retained for propagation or reporting."""
        self.errors = errors
        """Errors supplied through ``errors``."""
        self.message = self._summary(collected) if message is None else message
        """Override the summary message reported to the client."""

        super().__init__(self.message)

    @staticmethod
    def _summary(failures: tuple[ValidationFailure, ...]) -> str:
        """
        Build the summary message reported alongside the field errors.

        Parameters
        ----------
        failures : tuple[orionis.schemas.entities.failure.ValidationFailure, ``...``]
            Every failure collected for the payload.

        Returns
        -------
        str
            First failure message, suffixed with the remaining error count.
        """
        if not failures:
            return _DEFAULT_MESSAGE

        remaining = len(failures) - 1
        if not remaining:
            return failures[0].message

        plural = "s" if remaining > 1 else ""
        return f"{failures[0].message} (and {remaining} more error{plural})"

    def error(self) -> dict:
        """
        Return the summary and structured field errors as a dictionary.

        Returns
        -------
        dict
            ``message`` summary and ``errors`` mapping each field to a list
            of ``{rule, message}`` objects.
        """
        return {
            "message": self.message,
            "errors": self.errors,
        }
