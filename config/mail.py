from __future__ import annotations
from dataclasses import dataclass, field
from orionis.foundation.config.mail.entities.file import File
from orionis.foundation.config.mail.entities.from_address import FromAddress
from orionis.foundation.config.mail.entities.mail import Mail
from orionis.foundation.config.mail.entities.mailers import Mailers
from orionis.foundation.config.mail.entities.smtp import Smtp
from orionis.environment import Env

@dataclass(frozen=True, kw_only=True)
class BootstrapMail(Mail):

    # -------------------------------------------------------------------------
    # default : str, optional
    # --- The default mailer transport to use.
    # --- Uses the value from MAIL_MAILER or "smtp" if not set.
    # -------------------------------------------------------------------------
    default: str = field(
        default_factory=lambda: Env.get("MAIL_MAILER", "smtp"),
    )

    # -------------------------------------------------------------------------
    # from_address : FromAddress | dict, optional
    # --- The global sender applied to every message that declares no From.
    # --- Uses MAIL_FROM_ADDRESS and MAIL_FROM_NAME, falling back to APP_NAME.
    # -------------------------------------------------------------------------
    from_address: FromAddress | dict = field(
        default_factory=lambda: FromAddress(
            address = Env.get("MAIL_FROM_ADDRESS", ""),
            name = Env.get("MAIL_FROM_NAME", Env.get("APP_NAME", "Orionis")),
        ),
    )

    # -------------------------------------------------------------------------
    # mailers : Mailers | dict, optional
    # --- Collection of available mail transport configurations.
    # --- Uses Mailers instance with default values if not set.
    # -------------------------------------------------------------------------
    mailers: Mailers | dict = field(
        default_factory=lambda: Mailers(

            # -----------------------------------------------------------------
            # --- SMTP mail transport configuration.
            # --- Uses environment variables or sensible defaults.
            # -----------------------------------------------------------------
            smtp = Smtp(
                url = Env.get("MAIL_URL", ""),
                host = Env.get("MAIL_HOST", ""),
                port = Env.get("MAIL_PORT", 587),
                encryption = Env.get("MAIL_ENCRYPTION", "TLS"),
                username = Env.get("MAIL_USERNAME", ""),
                password = Env.get("MAIL_PASSWORD", ""),
                timeout = None,
            ),

            # -----------------------------------------------------------------
            # --- File mail transport configuration.
            # --- Stores emails in "storage/mail" directory by default.
            # -----------------------------------------------------------------
            file = File(
                path = "storage/mail",
            ),
        ),
    )
