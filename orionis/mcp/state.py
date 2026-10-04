"""Explicit authenticated MRTR state using Orionis' existing AEAD encrypter."""

import hashlib
import hmac
import time

import msgspec

from orionis.encrypter.contracts.encrypter import IEncrypter
from orionis.foundation.contracts.application import IApplication
from orionis.mcp.context import McpRequest, mutable_json
from orionis.mcp.exceptions import McpInvalidParams

# Runtime constructor annotations are consumed by Orionis' native DI container.
# ruff: noqa: TC001


class _State(msgspec.Struct, frozen=True):
    """Authenticate the complete structured envelope before exposing state."""

    purpose: str
    expires: float
    principal: str
    request: str
    value: object


_STATE_DECODER = msgspec.json.Decoder(_State)


class McpState:
    """Seal state across workers sharing an application key and GCM cipher."""

    __slots__ = ("_encrypter",)

    def __init__(self, app: IApplication, encrypter: IEncrypter) -> None:
        """Require authenticated encryption rather than unauthenticated CBC."""
        if app.config("app.cipher") not in ("AES-128-GCM", "AES-256-GCM"):
            message = "MCP requestState requires app.cipher AES-128-GCM or AES-256-GCM"
            raise ValueError(message)
        self._encrypter = encrypter

    def seal(self, request: McpRequest, value: object, *, ttl: int = 300) -> str:
        """Encrypt data bound to its principal, arguments, method and expiry."""
        if type(ttl) is not int or ttl <= 0:
            message = "State TTL must be a positive integer"
            raise ValueError(message)
        payload = {
            "purpose": "orionis.mcp.mrtr",
            "expires": time.time() + ttl,
            "principal": _principal(request),
            "request": _fingerprint(request),
            "value": value,
        }
        return self._encrypter.encrypt(msgspec.json.encode(payload).decode("utf-8"))

    def open(self, request: McpRequest) -> object:
        """Authenticate and validate client-carried state before using its data."""
        if not isinstance(request.request_state, str):
            msg = "Invalid request state"
            raise McpInvalidParams(msg)
        try:
            data = _STATE_DECODER.decode(self._encrypter.decrypt(request.request_state))
            valid = (
                data.purpose == "orionis.mcp.mrtr"
                and data.expires > time.time()
                and hmac.compare_digest(data.principal, _principal(request))
                and hmac.compare_digest(data.request, _fingerprint(request))
            )
            if valid:
                return data.value
        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as exc:
            msg = "Invalid request state"
            raise McpInvalidParams(msg) from exc
        msg = "Invalid request state"
        raise McpInvalidParams(msg)


def _fingerprint(request: McpRequest) -> str:
    """Bind state to stable request parameters, excluding retry and trace fields."""
    if not request.server_id:
        message = "MCP state requires a trusted server identifier"
        raise ValueError(message)
    data = {
        "server": request.server_id,
        "method": request.method,
        "uri": request.uri,
        "name": request.params.get("name"),
        "arguments": mutable_json(request.arguments),
    }
    encoded = msgspec.json.encode(data, order="deterministic")
    return hashlib.sha256(encoded).hexdigest()


def _principal(request: McpRequest) -> str:
    """Bind native guard, identity type, identifier and credential without coercion."""
    authentication = request.authentication
    identity = authentication.identity
    data = {
        "guard": authentication.guard,
        "type": None if identity is None else (
            f"{type(identity).__module__}.{type(identity).__qualname__}"
        ),
        "identifier": authentication.identifier(),
        "credential": authentication.credentialId,
        "abilities": None if authentication.abilities is None else (
            sorted(authentication.abilities)
        ),
    }
    return hashlib.sha256(msgspec.json.encode(data, order="deterministic")).hexdigest()
