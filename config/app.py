from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.app import App, Cipher, Environments

@dataclass(frozen=True, kw_only=True)
class BootstrapApp(App):
    # ----------------------------------------------------------------------------------
    # name : str, optional
    # --- The name of the application. Defaults to the value of the 'APP_NAME'
    # --- environment variable or 'Orionis Application'.
    # ----------------------------------------------------------------------------------
    name: str = field(
        default_factory=lambda: Env.get("APP_NAME", "Orionis Application"),
    )

    # ----------------------------------------------------------------------------------
    # env : str | Environments, optional
    # --- The environment in which the application runs. Defaults to the value of the
    # --- 'APP_ENV' environment variable or Environments.DEVELOPMENT.
    # ----------------------------------------------------------------------------------
    env: str | Environments = field(
        default_factory=lambda: Env.get("APP_ENV", Environments.DEVELOPMENT),
    )

    # ----------------------------------------------------------------------------------
    # debug : bool, optional
    # --- Whether debug mode is enabled. Defaults to the value of the 'APP_DEBUG'
    # --- environment variable or True.
    # ----------------------------------------------------------------------------------
    debug: bool = field(
        default_factory=lambda: Env.get("APP_DEBUG", True),
    )

    # ----------------------------------------------------------------------------------
    # timezone : str, optional
    # --- The timezone of the application. Defaults to the value of the 'APP_TIMEZONE'
    # --- environment variable or 'UTC'.
    # ----------------------------------------------------------------------------------
    timezone: str = field(
        default_factory=lambda: Env.get("APP_TIMEZONE", "UTC"),
    )

    # ----------------------------------------------------------------------------------
    # locale : str, optional
    # --- The locale for the application. Defaults to the value of the 'APP_LOCALE'
    # --- environment variable or 'en'.
    # ----------------------------------------------------------------------------------
    locale: str = field(
        default_factory=lambda: Env.get("APP_LOCALE", "en"),
    )

    # ----------------------------------------------------------------------------------
    # fallback_locale : str, optional
    # --- The locale used when a translation is missing. Defaults to the value of the
    # --- 'APP_FALLBACK_LOCALE' environment variable or 'en'.
    # ----------------------------------------------------------------------------------
    fallback_locale: str = field(
        default_factory=lambda: Env.get("APP_FALLBACK_LOCALE", "en"),
    )

    # ----------------------------------------------------------------------------------
    # language_path : str, optional
    # --- Relative path to the JSON translation files. Defaults to the value of the
    # --- 'APP_LANGUAGE_PATH' environment variable or 'resources/lang/'.
    # ----------------------------------------------------------------------------------
    language_path: str = field(
        default_factory=lambda: Env.get("APP_LANGUAGE_PATH", "resources/lang/"),
    )

    # ----------------------------------------------------------------------------------
    # cipher : str | Cipher, optional
    # --- The cipher used for encryption. Defaults to the value of the 'APP_CIPHER'
    # --- environment variable or Cipher.AES_256_CBC.
    # ----------------------------------------------------------------------------------
    cipher: str | Cipher = field(
        default_factory=lambda: Env.get("APP_CIPHER", Cipher.AES_256_CBC),
    )

    # ----------------------------------------------------------------------------------
    # key : str | bytes | None, optional
    # --- The encryption key for the application. Defaults to the value of the
    # --- 'APP_KEY' environment variable or None.
    # ----------------------------------------------------------------------------------
    key: str | bytes | None = field(
        default_factory=lambda: Env.get("APP_KEY", None),
    )

    # ----------------------------------------------------------------------------------
    # maintenance : bool, optional
    # --- Indicates whether the application is in maintenance mode. Defaults to the
    # --- value of the 'APP_MAINTENANCE' environment variable or False.
    # ----------------------------------------------------------------------------------
    maintenance: bool = field(
        default_factory=lambda: Env.get("APP_MAINTENANCE", False),
    )
