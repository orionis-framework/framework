from math import isfinite
from typing import TYPE_CHECKING
import msgspec
from orionis.realtime.decorators import MAX_TARGET_LENGTH
from orionis.realtime.errors import ProtocolError
if TYPE_CHECKING:
    from orionis.http.websocket_message import WebSocketMessage

MAX_ID_LENGTH = 128
MAX_ARGUMENTS = 64
MAX_ERROR_MESSAGE_LENGTH = 1024
MAX_ERROR_CODE_LENGTH = 64
_DEFAULT_MESSAGE_LIMIT = 1024 * 1024

class RPCErrorPayload(msgspec.Struct, frozen=True, forbid_unknown_fields=True):
    """Carry the public error returned by one completed invocation."""

    code: str
    message: str

class Invoke(
    msgspec.Struct, tag="invoke", frozen=True, forbid_unknown_fields=True,
):
    """Request one named server operation within a bounded invocation lifetime."""

    id: str
    target: str
    args: list[object] = msgspec.field(default_factory=list)
    kwargs: dict[str, object] = msgspec.field(default_factory=dict)
    timeout: float | None = None

class Completion(
    msgspec.Struct, tag="completion", frozen=True, forbid_unknown_fields=True,
):
    """Finish a pending server-to-client call with exactly one result or error."""

    id: str
    result: object = msgspec.UNSET
    error: RPCErrorPayload | msgspec.UnsetType = msgspec.UNSET

class Cancel(
    msgspec.Struct, tag="cancel", frozen=True, forbid_unknown_fields=True,
):
    """Cancel one active client-to-server invocation."""

    id: str

class Ping(msgspec.Struct, tag="ping", frozen=True, forbid_unknown_fields=True):
    """Request an application-level pong without creating a heartbeat task."""

class Pong(msgspec.Struct, tag="pong", frozen=True, forbid_unknown_fields=True):
    """Acknowledge an application-level ping."""

type ClientMessage = Invoke | Completion | Cancel | Ping | Pong

def validate_invocation_id(value: str) -> None:
    """
    Require a bounded printable identifier without interpreting its content.

    Parameters
    ----------
    value : str
        Client or server invocation identifier.

    Returns
    -------
    None
        Accept the opaque identifier.

    Raises
    ------
    ProtocolError
        If the identifier is empty, oversized, non-ASCII or contains spaces or
        nonprintable characters.
    """
    if (
        not value or len(value) > MAX_ID_LENGTH
        or not value.isascii() or not value.isprintable() or " " in value
    ):
        message = "Invalid invocation identifier"
        raise ProtocolError(message)

def _validate_invoke(message: Invoke) -> None:
    """
    Validate structural request limits beyond the decoded envelope types.

    Parameters
    ----------
    message : Invoke
        Typed incoming invocation.

    Returns
    -------
    None
        Accept bounded names, arguments and an optional positive timeout.

    Raises
    ------
    ProtocolError
        If an invocation exceeds a structural limit.
    """
    validate_invocation_id(message.id)
    if not message.target or len(message.target) > MAX_TARGET_LENGTH:
        error = "Invalid invocation target"
        raise ProtocolError(error)
    if (
        len(message.args) > MAX_ARGUMENTS or len(message.kwargs) > MAX_ARGUMENTS
        or any(not key or len(key) > MAX_TARGET_LENGTH for key in message.kwargs)
    ):
        error = "Invocation arguments exceed protocol limits"
        raise ProtocolError(error)
    if message.timeout is not None and (
        message.timeout <= 0 or not isfinite(message.timeout)
    ):
        error = "Invocation timeout must be finite and positive"
        raise ProtocolError(error)

def _validate_completion(message: Completion) -> None:
    """
    Require exactly one completion outcome and bounded public error text.

    Parameters
    ----------
    message : Completion
        Typed client response.

    Returns
    -------
    None
        Accept one outcome including an explicit null result.

    Raises
    ------
    ProtocolError
        If the identifier, outcome or public error fields are invalid.
    """
    validate_invocation_id(message.id)
    if (message.result is msgspec.UNSET) == (message.error is msgspec.UNSET):
        error = "Completion requires exactly one result or error"
        raise ProtocolError(error)
    if isinstance(message.error, RPCErrorPayload) and (
        not message.error.code or len(message.error.code) > MAX_ERROR_CODE_LENGTH
        or len(message.error.message) > MAX_ERROR_MESSAGE_LENGTH
    ):
        error = "Completion error exceeds protocol limits"
        raise ProtocolError(error)

class HubProtocol:
    """Encode Orionis Realtime v1 using route-selected JSON or MessagePack."""

    __slots__ = ("_decoder", "_encoder", "_max_message_size", "name")

    def __init__(
        self, name: str = "json", *, max_message_size: int = _DEFAULT_MESSAGE_LIMIT,
    ) -> None:
        """
        Prepare reusable msgspec codecs without connection or task ownership.

        Parameters
        ----------
        name : str, optional
            ``json`` for text frames or ``msgpack`` for binary frames.
        max_message_size : int, optional
            Maximum incoming UTF-8 or binary byte length.

        Returns
        -------
        None
            Prepare the selected protocol codec.

        Raises
        ------
        ValueError
            If the codec is unknown or the message limit is not a positive,
            nonboolean integer.
        """
        if name not in {"json", "msgpack"}:
            message = "Realtime protocol must be 'json' or 'msgpack'"
            raise ValueError(message)
        if (
            not isinstance(max_message_size, int) or isinstance(max_message_size, bool)
            or max_message_size < 1
        ):
            message = "Realtime message limit must be a positive integer"
            raise ValueError(message)
        self.name = name
        self._max_message_size = max_message_size
        codec = msgspec.json if name == "json" else msgspec.msgpack
        self._decoder = codec.Decoder(ClientMessage)
        self._encoder = codec.Encoder()

    def decode(self, message: WebSocketMessage) -> ClientMessage:
        """
        Decode and validate one client envelope from a complete socket message.

        Parameters
        ----------
        message : WebSocketMessage
            Text JSON or binary MessagePack message selected by the route.

        Returns
        -------
        ClientMessage
            Strict typed request, completion, cancellation or ping/pong.

        Raises
        ------
        ProtocolError
            If frame kind, size, fields or structural limits are invalid.
        """
        if self.name == "json":
            if not message.isText():
                error = "JSON realtime protocol requires text frames"
                raise ProtocolError(error, close_code=1003)
            data = message.text
            size = len(data) if data.isascii() else len(data.encode("utf-8"))
        else:
            if not message.isBytes():
                error = "MessagePack realtime protocol requires binary frames"
                raise ProtocolError(error, close_code=1003)
            data = message.bytes
            size = len(data)
        if size > self._max_message_size:
            error = "Realtime message exceeds configured size"
            raise ProtocolError(error, close_code=1009)
        try:
            decoder = self._decoder
            decoded = (
                decoder.decode(data) if isinstance(decoder, msgspec.json.Decoder)
                else decoder.decode(message.bytes)
            )
        except (msgspec.DecodeError, RecursionError) as exc:
            raise ProtocolError from exc
        if isinstance(decoded, Invoke):
            _validate_invoke(decoded)
        elif isinstance(decoded, Completion):
            _validate_completion(decoded)
        elif isinstance(decoded, Cancel):
            validate_invocation_id(decoded.id)
        return decoded

    def encode(self, message: object) -> str | bytes:
        """
        Encode an outgoing envelope once for direct send or broadcast reuse.

        Parameters
        ----------
        message : object
            Framework-owned envelope containing a serializable result or event.

        Returns
        -------
        str | bytes
            Text JSON or binary MessagePack payload.

        Raises
        ------
        TypeError
            If an application result cannot be encoded.
        """
        payload = self._encoder.encode(message)
        return payload.decode("utf-8") if self.name == "json" else payload
