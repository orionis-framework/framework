from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Self
from urllib.parse import unquote, urlsplit
from orionis.mail.enums.encryption import MailEncryption
from orionis.mail.exceptions import MailConfigurationException

if TYPE_CHECKING:
    from collections.abc import Mapping

_MAX_PORT = 65535
_DEFAULT_PORT = 587
_SMTPS_PORT = 465
_FIRST_PRINTABLE = 32

# Accepted encryption names, including the empty string that a configuration
# uses to request an explicit plaintext connection.
_ENCRYPTIONS: dict[str, MailEncryption] = {
    "tls": MailEncryption.TLS,
    "ssl": MailEncryption.SSL,
    "none": MailEncryption.NONE,
    "": MailEncryption.NONE,
}

@dataclass(frozen=True, slots=True, kw_only=True)
class SmtpSettings:
    """
    Store effective SMTP settings without exposing credentials in repr.

    Parameters
    ----------
    host : str
        Effective SMTP hostname.
    port : int
        Effective TCP port between 1 and 65535.
    encryption : MailEncryption
        Negotiated transport security mode.
    username : str
        Authentication user, empty when authentication is disabled.
    password : str
        Authentication secret, empty when authentication is disabled.
    timeout : int | None
        Positive socket timeout in seconds, or None for an unbounded wait.
    sensitive : tuple[str, ...]
        Values redacted from transport diagnostics.
    """

    host: str
    port: int
    encryption: MailEncryption
    username: str = field(repr=False)
    password: str = field(repr=False)
    timeout: int | None
    sensitive: tuple[str, ...] = field(repr=False)

    @classmethod
    def fromConfig(cls, config: Mapping[str, object]) -> Self:
        """
        Resolve URL precedence and validate the effective SMTP settings.

        Parameters
        ----------
        config : Mapping[str, object]
            One normalized mailer, without environment lookups.

        Returns
        -------
        Self
            Validated immutable connection options.

        Raises
        ------
        MailConfigurationException
            If endpoint, encryption, credentials, timeout, or URL is invalid.
        """
        url = _text(config, "url", "")
        effective = {**config, **_url_overrides(url)}
        host = _text(effective, "host", "")
        port = _port(effective.get("port", _DEFAULT_PORT))
        mode = _text(effective, "encryption", MailEncryption.TLS).lower()
        username = _text(effective, "username", "")
        password = _text(effective, "password", "")
        timeout = _timeout(config.get("timeout"))

        if not host or _has_controls(host) or any(char in host for char in "/\\@"):
            error_msg = "The selected SMTP mailer requires a valid host."
            raise MailConfigurationException(error_msg)
        if mode not in _ENCRYPTIONS:
            error_msg = "SMTP encryption must be TLS, SSL, none, or an empty string."
            raise MailConfigurationException(error_msg)
        if bool(username) != bool(password):
            error_msg = "SMTP authentication requires both username and password."
            raise MailConfigurationException(error_msg)

        # Keep every credential spelling that a server response could echo,
        # including the ones replaced by the URL.
        sensitive = (
            url,
            username,
            password,
            unquote(url),
            config.get("username"),
            config.get("password"),
        )
        return cls(
            host=host,
            port=port,
            encryption=_ENCRYPTIONS[mode],
            username=username,
            password=password,
            timeout=timeout,
            sensitive=tuple(value for value in sensitive if isinstance(value, str)),
        )

def _text(config: Mapping[str, object], key: str, default: str) -> str:
    """
    Read a string setting without including its value in errors.

    Parameters
    ----------
    config : Mapping[str, object]
        Effective connection options.
    key : str
        Option name.
    default : str
        Value used when the option is absent.

    Returns
    -------
    str
        Unmodified setting.

    Raises
    ------
    MailConfigurationException
        If a setting is not a string.
    """
    value = config.get(key, default)
    if not isinstance(value, str):
        error_msg = f"SMTP {key} must be a string."
        raise MailConfigurationException(error_msg)
    return value

def _port(value: object) -> int:
    """
    Validate the effective SMTP TCP port.

    Parameters
    ----------
    value : object
        Port after applying URL precedence.

    Returns
    -------
    int
        Port inside the TCP range.

    Raises
    ------
    MailConfigurationException
        If the port is not an integer between 1 and 65535.
    """
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= _MAX_PORT
    ):
        error_msg = "SMTP port must be an integer between 1 and 65535."
        raise MailConfigurationException(error_msg)
    return value

def _timeout(value: object) -> int | None:
    """
    Validate a blocking SMTP timeout without silently replacing None.

    Parameters
    ----------
    value : object
        Configured integer seconds, or None.

    Returns
    -------
    int | None
        Explicit timeout; None means an unbounded socket wait.

    Raises
    ------
    MailConfigurationException
        If the timeout is not a positive integer or None.
    """
    if value is None:
        return None

    # Blocking smtplib rejects a zero timeout because it would create a
    # non-blocking socket.
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        error_msg = "SMTP timeout must be a positive integer or None."
        raise MailConfigurationException(error_msg)
    return value

def _url_overrides(url: str) -> dict[str, object]:
    """
    Parse the supported MAIL_URL components with explicit precedence.

    Parameters
    ----------
    url : str
        Empty string, smtp URL, or smtps URL without extra components.

    Returns
    -------
    dict[str, object]
        Only the options supplied or forced by the URL.

    Raises
    ------
    MailConfigurationException
        If the URL is malformed or includes unsupported components.
    """
    if not url:
        return {}

    try:
        parsed = urlsplit(url)
        invalid = (
            parsed.scheme not in {"smtp", "smtps"}
            or not parsed.hostname
            or parsed.path
            or "?" in url
            or "#" in url
            or _has_controls(url)
            or parsed.netloc.endswith(":")
        )
        if invalid:
            error_msg = "MAIL_URL requires smtp/smtps, a host, and no extra components."
            raise MailConfigurationException(error_msg)

        values: dict[str, object] = {"host": parsed.hostname}
        if parsed.scheme == "smtps":
            values.update(encryption=MailEncryption.SSL, port=_SMTPS_PORT)
        if parsed.port is not None:
            values["port"] = parsed.port

        # URL credentials replace both individual fields as a single unit.
        if parsed.username is not None or parsed.password is not None:
            values["username"] = unquote(parsed.username or "", errors="strict")
            values["password"] = unquote(parsed.password or "", errors="strict")
        return values
    except ValueError:
        error_msg = "MAIL_URL contains an invalid host, port, or encoded credential."
        raise MailConfigurationException(error_msg) from None

def _has_controls(value: str) -> bool:
    """
    Detect forbidden whitespace and ASCII controls in an endpoint.

    Parameters
    ----------
    value : str
        URL or hostname.

    Returns
    -------
    bool
        Whether the endpoint contains forbidden characters.
    """
    return any(char.isspace() or ord(char) < _FIRST_PRINTABLE for char in value)
