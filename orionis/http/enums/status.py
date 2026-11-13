"""Provide http enums operations through ``HTTPStatus``, ``WebSocketStatus``."""

from enum import IntEnum


class HTTPStatus(IntEnum):
    """Enumerate HTTP response status codes supported by the framework."""

    CONTINUE = 100
    """Continue value used by ``HTTPStatus``."""
    SWITCHING_PROTOCOLS = 101
    """Switching protocols value used by ``HTTPStatus``."""
    PROCESSING = 102
    """Processing value used by ``HTTPStatus``."""
    EARLY_HINTS = 103
    """Early hints value used by ``HTTPStatus``."""
    OK = 200
    """Ok value used by ``HTTPStatus``."""
    CREATED = 201
    """Created value used by ``HTTPStatus``."""
    ACCEPTED = 202
    """Accepted value used by ``HTTPStatus``."""
    NON_AUTHORITATIVE_INFORMATION = 203
    """Non authoritative information value used by ``HTTPStatus``."""
    NO_CONTENT = 204
    """No content value used by ``HTTPStatus``."""
    RESET_CONTENT = 205
    """Reset content value used by ``HTTPStatus``."""
    PARTIAL_CONTENT = 206
    """Partial content value used by ``HTTPStatus``."""
    MULTI_STATUS = 207
    """Multi status value used by ``HTTPStatus``."""
    ALREADY_REPORTED = 208
    """Already reported value used by ``HTTPStatus``."""
    IM_USED = 226
    """Im used value used by ``HTTPStatus``."""
    MULTIPLE_CHOICES = 300
    """Multiple choices value used by ``HTTPStatus``."""
    MOVED_PERMANENTLY = 301
    """Moved permanently value used by ``HTTPStatus``."""
    FOUND = 302
    """Found value used by ``HTTPStatus``."""
    SEE_OTHER = 303
    """See other value used by ``HTTPStatus``."""
    NOT_MODIFIED = 304
    """Not modified value used by ``HTTPStatus``."""
    USE_PROXY = 305
    """Use proxy value used by ``HTTPStatus``."""
    UNUSED = 306
    """Unused value used by ``HTTPStatus``."""
    TEMPORARY_REDIRECT = 307
    """Temporary redirect value used by ``HTTPStatus``."""
    PERMANENT_REDIRECT = 308
    """Permanent redirect value used by ``HTTPStatus``."""
    BAD_REQUEST = 400
    """Bad request value used by ``HTTPStatus``."""
    UNAUTHORIZED = 401
    """Unauthorized value used by ``HTTPStatus``."""
    PAYMENT_REQUIRED = 402
    """Payment required value used by ``HTTPStatus``."""
    FORBIDDEN = 403
    """Forbidden value used by ``HTTPStatus``."""
    NOT_FOUND = 404
    """Not found value used by ``HTTPStatus``."""
    METHOD_NOT_ALLOWED = 405
    """Method not allowed value used by ``HTTPStatus``."""
    NOT_ACCEPTABLE = 406
    """Not acceptable value used by ``HTTPStatus``."""
    PROXY_AUTHENTICATION_REQUIRED = 407
    """Proxy authentication required value used by ``HTTPStatus``."""
    REQUEST_TIMEOUT = 408
    """Request timeout value used by ``HTTPStatus``."""
    CONFLICT = 409
    """Conflict value used by ``HTTPStatus``."""
    GONE = 410
    """Gone value used by ``HTTPStatus``."""
    LENGTH_REQUIRED = 411
    """Length required value used by ``HTTPStatus``."""
    PRECONDITION_FAILED = 412
    """Precondition failed value used by ``HTTPStatus``."""
    CONTENT_TOO_LARGE = 413
    """Content too large value used by ``HTTPStatus``."""
    URI_TOO_LONG = 414
    """Uri too long value used by ``HTTPStatus``."""
    UNSUPPORTED_MEDIA_TYPE = 415
    """Unsupported media type value used by ``HTTPStatus``."""
    RANGE_NOT_SATISFIABLE = 416
    """Range not satisfiable value used by ``HTTPStatus``."""
    EXPECTATION_FAILED = 417
    """Expectation failed value used by ``HTTPStatus``."""
    IM_A_TEAPOT = 418
    """Im a teapot value used by ``HTTPStatus``."""
    PAGE_EXPIRED = 419
    """Page expired value used by ``HTTPStatus``."""
    MISDIRECTED_REQUEST = 421
    """Misdirected request value used by ``HTTPStatus``."""
    UNPROCESSABLE_CONTENT = 422
    """Unprocessable content value used by ``HTTPStatus``."""
    LOCKED = 423
    """Locked value used by ``HTTPStatus``."""
    FAILED_DEPENDENCY = 424
    """Failed dependency value used by ``HTTPStatus``."""
    TOO_EARLY = 425
    """Too early value used by ``HTTPStatus``."""
    UPGRADE_REQUIRED = 426
    """Upgrade required value used by ``HTTPStatus``."""
    PRECONDITION_REQUIRED = 428
    """Precondition required value used by ``HTTPStatus``."""
    TOO_MANY_REQUESTS = 429
    """Too many requests value used by ``HTTPStatus``."""
    REQUEST_HEADER_FIELDS_TOO_LARGE = 431
    """Request header fields too large value used by ``HTTPStatus``."""
    UNAVAILABLE_FOR_LEGAL_REASONS = 451
    """Unavailable for legal reasons value used by ``HTTPStatus``."""
    INTERNAL_SERVER_ERROR = 500
    """Internal server error value used by ``HTTPStatus``."""
    NOT_IMPLEMENTED = 501
    """Not implemented value used by ``HTTPStatus``."""
    BAD_GATEWAY = 502
    """Bad gateway value used by ``HTTPStatus``."""
    SERVICE_UNAVAILABLE = 503
    """Service unavailable value used by ``HTTPStatus``."""
    GATEWAY_TIMEOUT = 504
    """Gateway timeout value used by ``HTTPStatus``."""
    HTTP_VERSION_NOT_SUPPORTED = 505
    """Http version not supported value used by ``HTTPStatus``."""
    VARIANT_ALSO_NEGOTIATES = 506
    """Variant also negotiates value used by ``HTTPStatus``."""
    INSUFFICIENT_STORAGE = 507
    """Insufficient storage value used by ``HTTPStatus``."""
    LOOP_DETECTED = 508
    """Loop detected value used by ``HTTPStatus``."""
    NOT_EXTENDED = 510
    """Not extended value used by ``HTTPStatus``."""
    NETWORK_AUTHENTICATION_REQUIRED = 511
    """Network authentication required value used by ``HTTPStatus``."""


class WebSocketStatus(IntEnum):
    """Enumerate WebSocket close status codes."""

    NORMAL_CLOSURE = 1000
    """Normal closure value used by ``WebSocketStatus``."""
    GOING_AWAY = 1001
    """Going away value used by ``WebSocketStatus``."""
    PROTOCOL_ERROR = 1002
    """Protocol error value used by ``WebSocketStatus``."""
    UNSUPPORTED_DATA = 1003
    """Unsupported data value used by ``WebSocketStatus``."""
    RESERVED = 1004
    """Reserved value used by ``WebSocketStatus``."""
    NO_STATUS_RCVD = 1005
    """No status rcvd value used by ``WebSocketStatus``."""
    ABNORMAL_CLOSURE = 1006
    """Abnormal closure value used by ``WebSocketStatus``."""
    INVALID_FRAME_PAYLOAD_DATA = 1007
    """Invalid frame payload data value used by ``WebSocketStatus``."""
    POLICY_VIOLATION = 1008
    """Policy violation value used by ``WebSocketStatus``."""
    MESSAGE_TOO_BIG = 1009
    """Message too big value used by ``WebSocketStatus``."""
    MANDATORY_EXT = 1010
    """Mandatory ext value used by ``WebSocketStatus``."""
    INTERNAL_ERROR = 1011
    """Internal error value used by ``WebSocketStatus``."""
    SERVICE_RESTART = 1012
    """Service restart value used by ``WebSocketStatus``."""
    TRY_AGAIN_LATER = 1013
    """Try again later value used by ``WebSocketStatus``."""
    BAD_GATEWAY = 1014
    """Bad gateway value used by ``WebSocketStatus``."""
    TLS_HANDSHAKE = 1015
    """Tls handshake value used by ``WebSocketStatus``."""
    UNAUTHORIZED = 3000
    """Unauthorized value used by ``WebSocketStatus``."""
    FORBIDDEN = 3003
    """Forbidden value used by ``WebSocketStatus``."""
    TIMEOUT = 3008
    """Timeout value used by ``WebSocketStatus``."""
