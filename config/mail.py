from __future__ import annotations
from dataclasses import dataclass, field
from orionis.environment import Env
from orionis.foundation.config.mail import (
    File, FromAddress, Mail, MailDriver, Mailers, Smtp,
)

@dataclass(frozen=True, kw_only=True)
class BootstrapMail(Mail):
    # ----------------------------------------------------------------------------------
    # default : str | MailDriver, optional
    # --- The default mailer transport to use.
    # --- Uses the value from MAIL_MAILER or "smtp" if not set.
    # ----------------------------------------------------------------------------------
    default: str | MailDriver = field(
        default_factory=lambda: Env.get("MAIL_MAILER", MailDriver.SMTP),
    )

    # ----------------------------------------------------------------------------------
    # from_address : FromAddress | dict, optional
    # --- The global sender applied to every message that declares no From.
    # --- Uses MAIL_FROM_ADDRESS and MAIL_FROM_NAME, falling back to APP_NAME.
    # ----------------------------------------------------------------------------------
    from_address: FromAddress | dict = field(
        default_factory=lambda: FromAddress(
            address=Env.get("MAIL_FROM_ADDRESS", ""),
            name=Env.get("MAIL_FROM_NAME", Env.get("APP_NAME", "Orionis")),
        ),
    )

    # ----------------------------------------------------------------------------------
    # mailers : Mailers | dict, optional
    # --- Collection of available mail transport configurations.
    # --- Configure each transport's environment keys and fallback values here.
    # ----------------------------------------------------------------------------------
    mailers: Mailers | dict = field(
        default_factory=lambda: Mailers(
            # --------------------------------------------------------------------------
            # smtp : Smtp, optional
            # --- SMTP mail transport configuration.
            # --- Uses environment variables or sensible defaults.
            # --------------------------------------------------------------------------
            smtp=Smtp(
                url=Env.get("MAIL_URL", ""),
                host=Env.get("MAIL_HOST", ""),
                port=Env.get("MAIL_PORT", 587),
                encryption=Env.get("MAIL_ENCRYPTION", "TLS"),
                username=Env.get("MAIL_USERNAME", ""),
                password=Env.get("MAIL_PASSWORD", ""),
                timeout=Env.get("MAIL_TIMEOUT", None),
            ),
            # --------------------------------------------------------------------------
            # file : File, optional
            # --- File mail transport configuration.
            # --- Stores emails in "storage/mail" directory by default.
            # --------------------------------------------------------------------------
            file=File(
                path=Env.get("MAIL_FILE_PATH", "storage/mail"),
            ),
        ),
    )
