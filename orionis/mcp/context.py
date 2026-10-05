from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Literal
import msgspec
from orionis.auth.context.functions import current_auth_context

if TYPE_CHECKING:
    from orionis.auth.contracts.authenticatable import IAuthenticatable
    from orionis.auth.contracts.context import IAuthenticationContext
    from orionis.http.request import Request

def freeze_json(value: object) -> object:
    """
    Copy JSON containers into recursively immutable request snapshots.

    Parameters
    ----------
    value : object
        Value to inspect, transform or validate.

    Returns
    -------
    object
        Result of the operation described above.
    """
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze_json(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze_json(item) for item in value)
    return value

def mutable_json(value: object) -> object:
    """
    Copy a request snapshot into standard containers for msgspec validation.

    Parameters
    ----------
    value : object
        Value to inspect, transform or validate.

    Returns
    -------
    object
        Result of the operation described above.
    """
    if isinstance(value, Mapping):
        return {key: mutable_json(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [mutable_json(item) for item in value]
    return value

@dataclass(frozen=True, slots=True, kw_only=True)
class McpRequest:
    """Hold only explicit input and native context for one independent call."""

    id: str | int
    method: str
    server_id: str = ""
    meta: Mapping[str, object] = field(default_factory=dict)
    arguments: Mapping[str, object] = field(default_factory=dict)
    params: Mapping[str, object] = field(default_factory=dict)
    uri_variables: Mapping[str, object] = field(default_factory=dict)
    uri: str | None = None
    input_responses: Mapping[str, object] = field(default_factory=dict)
    request_state: str | msgspec.UnsetType = msgspec.UNSET
    transport: Literal["http", "stdio", "test"] = "test"
    authentication: IAuthenticationContext = field(default_factory=current_auth_context)
    native_request: Request | None = None

    def __post_init__(self) -> None:
        """
        Detach client mappings and make every nested container read-only.

        Returns
        -------
        None
            Complete the documented operation without returning a value.
        """
        for name in ("meta", "arguments", "params", "uri_variables", "input_responses"):
            object.__setattr__(self, name, freeze_json(getattr(self, name)))

    @property
    def identity(self) -> IAuthenticatable | None:
        """
        Read identity through Orionis' scoped authentication lifecycle.

        Returns
        -------
        IAuthenticatable | None
            Result of the operation described above.
        """
        return self.authentication.identity

    @property
    def client_capabilities(self) -> Mapping[str, object]:
        """
        Read capabilities declared on this request, never a previous call.

        Returns
        -------
        Mapping[str, object]
            Result of the operation described above.
        """
        value = self.meta.get("io.modelcontextprotocol/clientCapabilities", {})
        return value if isinstance(value, Mapping) else MappingProxyType({})

McpContext = McpRequest
