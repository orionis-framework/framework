from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

@dataclass(frozen=True, slots=True, kw_only=True)
class AccessToken:
    """Describe a stored personal access token.

    The secret itself is never part of this entity, only the metadata
    needed to accept, restrict and audit the credential.

    Attributes
    ----------
    id : object
        Primary key of the token row.
    tokenable_type : str
        Polymorphic type of the identity owning the token.
    tokenable_id : object
        Identifier of the identity owning the token.
    name : str
        Human readable label describing the token.
    abilities : frozenset[str] | None
        Abilities the token may use, or ``None`` when the token keeps the
        full authorization of the identity.
    created_at : datetime | None
        Moment the token was issued.
    expires_at : datetime | None
        Moment the token stops being accepted.
    last_used_at : datetime | None
        Moment the token was last presented on a request.
    revoked_at : datetime | None
        Moment the token was revoked.
    """

    id: object
    tokenable_type: str
    tokenable_id: object
    name: str
    abilities: frozenset[str] | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None
    last_used_at: datetime | None = None
    revoked_at: datetime | None = None

    def toDict(self) -> dict[str, object]:
        """Serialize token metadata without any usable credential material.

        Returns
        -------
        dict[str, object]
            Metadata suitable for listing or auditing issued credentials.
        """
        return asdict(self)
