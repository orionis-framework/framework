# ruff: noqa: TC001
# Keep runtime annotations, guarded exits, and framework integration explicit.
"""Pair a freshly issued token with its plain text value."""

from dataclasses import dataclass, field
from orionis.auth.entities.access_token import AccessToken


@dataclass(frozen=True, slots=True, kw_only=True)
class NewAccessToken:
    """
    Pair a freshly issued token with its plain text value.

    The plain text value only exists in the return value of the call that
    issued the token. It is never persisted and cannot be recovered later.

    Attributes
    ----------
    access_token : orionis.auth.entities.AccessToken
        Metadata of the stored token.
    plain_text : str
        Value the client must send in the ``Authorization`` header. It is
        excluded from ``repr()`` so it never leaks into logs or tracebacks.
    """

    access_token: AccessToken
    plain_text: str = field(repr=False)

    def toDict(self) -> dict[str, object]:
        """
        Serialize only public metadata; access plain_text explicitly to issue it.

        Returns
        -------
        dict[str, object]
            Redacted token metadata excluding the plain text credential.
        """
        return {"access_token": self.access_token.toDict()}
