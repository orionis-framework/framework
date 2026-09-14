from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.auth.contracts.authenticatable import IAuthenticatable

@dataclass(frozen=True, slots=True, kw_only=True)
class GuardResult:
    """Carry what a guard learned about the incoming request.

    Attributes
    ----------
    identity : IAuthenticatable
        Identity resolved from the presented credential.
    guard : str
        Name of the guard that resolved the identity.
    abilities : frozenset[str] | None
        Abilities restricting the presented credential, or ``None`` when
        the credential keeps the full authorization of the identity.
    credential_id : object | None
        Identifier of the credential used, when the guard works with
        revocable credentials such as personal access tokens.
    """

    identity: IAuthenticatable
    guard: str
    abilities: frozenset[str] | None = None
    credential_id: object | None = None
