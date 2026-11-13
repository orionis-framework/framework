# ruff: noqa: PLC0415
# Resolve key generation only when validated application configuration needs it.
"""Represent application configuration settings."""

import base64
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from orionis.environment import Env
from orionis.foundation.config.app.enums import Cipher, Environments
from orionis.foundation.config.app.enums.ciphers import _AUTHENTICATED_CIPHERS
from orionis.foundation.config.validation import (
    normalize_enum,
    validate_boolean,
    validate_string,
)
from orionis.support.entities.base import BaseEntity


@dataclass(frozen=True, kw_only=True)
class App(BaseEntity):
    """
    Represent application configuration settings.

    Attributes
    ----------
    name : str, optional
        The name of the application. Default is 'Orionis Application'.
    env : str | orionis.foundation.config.app.Environments, optional
        The environment in which the application is running. Default is
        'DEVELOPMENT'.
    debug : bool, optional
        Whether debug mode is enabled. Default is True.
    timezone : str, optional
        The timezone of the application. Default is 'UTC'.
    locale : str, optional
        The locale for the application. Default is 'en'.
    fallback_locale : str, optional
        The locale used when a translation is missing. Default is 'en'.
    language_path : str, optional
        Relative path to the JSON translation files. Default is
        'resources/lang/'.
    cipher : str | orionis.foundation.config.app.Cipher, optional
        The authenticated cipher used for encryption. Default is 'AES-256-GCM'.
    key : str | bytes | None, optional
        The encryption key, normalized to bytes. None generates a persistent key.
    maintenance : bool, optional
        Whether maintenance mode is enabled. Default is False.
    """

    name: str = field(
        default_factory=lambda: Env.get("APP_NAME", "Orionis Application"),
        metadata={
            "description": "The name of the application. Defaults to "
            "'Orionis Application'.",
            "default": "Orionis Application",
        },
    )

    env: str | Environments = field(
        default_factory=lambda: Env.get("APP_ENV", Environments.DEVELOPMENT.value),
        metadata={
            "description": "The environment in which the application is running. "
            "Defaults to 'DEVELOPMENT'.",
            "default": "development",
        },
    )

    debug: bool = field(
        default_factory=lambda: Env.get("APP_DEBUG", True),
        metadata={
            "description": "Flag indicating whether debug mode is enabled. "
            "Defaults to True.",
            "default": True,
        },
    )

    timezone: str = field(
        default_factory=lambda: Env.get("APP_TIMEZONE", "UTC"),
        metadata={
            "description": "The timezone of the application. Defaults to 'UTC'.",
            "default": "UTC",
        },
    )

    locale: str = field(
        default_factory=lambda: Env.get("APP_LOCALE", "en"),
        metadata={
            "description": "The locale for the application. Defaults to 'en'.",
            "default": "en",
        },
    )

    fallback_locale: str = field(
        default_factory=lambda: Env.get("APP_FALLBACK_LOCALE", "en"),
        metadata={
            "description": "The locale used when a translation is missing. "
            "Defaults to 'en'.",
            "default": "en",
        },
    )

    language_path: str = field(
        default_factory=lambda: Env.get("APP_LANGUAGE_PATH", "resources/lang/"),
        metadata={
            "description": "Relative path to the JSON translation files. "
            "Defaults to 'resources/lang/'.",
            "default": "resources/lang/",
        },
    )

    cipher: str | Cipher = field(
        default_factory=lambda: Env.get("APP_CIPHER", Cipher.AES_256_GCM.value),
        metadata={
            "description": "The authenticated cipher. Defaults to 'AES-256-GCM'.",
            "default": "AES-256-GCM",
        },
    )

    key: str | bytes | None = field(
        default_factory=lambda: Env.get("APP_KEY"),
        metadata={
            "description": "The encryption key for the application. Defaults to None.",
            "default": None,
        },
    )

    maintenance: bool = field(
        default_factory=lambda: Env.get("APP_MAINTENANCE", False),
        metadata={
            "description": "Indicates whether the application is in maintenance mode.",
            "default": False,
        },
    )

    def __post_init__(self) -> None:
        """Validate application options and normalize their values.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        ValueError
            If the cipher is not authenticated or another setting is invalid.
        """
        super().__post_init__()

        # Validate scalar options before normalizing enum-backed values.
        for name in ("name", "timezone", "locale", "fallback_locale", "language_path"):
            validate_string(getattr(self, name), name)
        validate_boolean(self.debug, "debug")
        validate_boolean(self.maintenance, "maintenance")

        # Store enum configuration as its canonical enum values.
        object.__setattr__(self, "env", normalize_enum(self.env, Environments, "env"))
        object.__setattr__(
            self,
            "cipher",
            normalize_enum(self.cipher, Cipher, "cipher"),
        )
        if self.cipher not in _AUTHENTICATED_CIPHERS:
            message = (
                "'cipher' must use authenticated AES-GCM; legacy CBC is not supported."
            )
            raise ValueError(message)

        # Reject timezones that the standard library cannot resolve.
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            message = "'timezone' must identify a valid timezone."
            raise ValueError(message) from exc

        self.__validateKey()

    def __validateKey(self) -> None:
        """Validate and normalize the encryption key for cipher consumers.

        Returns
        -------
        None
            No return value.
        """
        # Resolve key support after the application configuration module is loaded.
        from orionis.environment.key.key_generator import (
            SecureKeyGenerator,
        )

        # Generate a key only when the configuration does not provide one.
        generated = self.key is None
        key = SecureKeyGenerator.generate(self.cipher) if generated else self.key
        if not isinstance(key, (bytes, str)) or not key:
            message = "The 'key' attribute must be non-empty bytes or a string."
            raise TypeError(message)
        if isinstance(key, str):
            # Decode the framework's explicit base64 key representation.
            try:
                raw_key = (
                    base64.b64decode(key[7:], validate=True)
                    if key.startswith("base64:")
                    else key.encode("utf-8")
                )
            except ValueError as exc:
                message = "The 'key' attribute contains invalid base64."
                raise ValueError(message) from exc
        else:
            raw_key = key

        # Enforce the exact key length required by the selected cipher.
        required_size = SecureKeyGenerator.KEY_SIZES[Cipher(self.cipher)]
        if len(raw_key) != required_size:
            message = f"The configured cipher requires a {required_size}-byte key."
            raise ValueError(message)
        if generated:
            Env.set("APP_KEY", key)
        object.__setattr__(self, "key", raw_key)
