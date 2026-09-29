from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from inspect import isawaitable
from typing import TYPE_CHECKING, cast
from orionis.foundation.contracts.application import IApplication
from orionis.mail.composer import MailComposer
from orionis.mail.contracts.manager import IMailManager
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.entities.address import Address
from orionis.mail.entities.envelope import Envelope
from orionis.mail.exceptions import MailConfigurationException
from orionis.mail.functions import freeze_owned
from orionis.mail.pending import PendingMail
from orionis.mail.transports.file import create_file_transport
from orionis.mail.transports.smtp import create_smtp_transport
from orionis.support.entities.base import BaseEntity

if TYPE_CHECKING:
    from orionis.mail.entities.attachment import Attachment
    from orionis.mail.entities.content import Content
    from orionis.mail.entities.result import MailResult
    from orionis.mail.types import TransportFactory

# Mailer names whose driver may be omitted in the configuration.
_CONVENTIONAL_DRIVERS = frozenset({"smtp", "file"})

class MailManager(PendingMail, IMailManager):
    """
    Resolve central mail configuration and delegate the shared fluent pipeline.

    The inherited empty chain is never mutated: every fluent entry creates a
    new PendingMail. No operation envelope, body, or attachment is cached on
    the manager, and factories run per send so they may resolve shared
    stateless transports through the container.

    Concurrency
    -----------
    Driver registration is synchronous and rejects duplicates, so drivers must
    be registered during provider startup, before concurrent sends. Transport
    resolution and preparation keep all per-operation state in local variables.
    """

    # ruff: noqa: TC001

    __slots__ = ("_app", "_composer", "_factories")

    def __init__(self, app: IApplication, composer: MailComposer) -> None:
        """
        Retain shared dependencies without validating or opening transports.

        Parameters
        ----------
        app : IApplication
            Central configuration and dependency container.
        composer : MailComposer
            Single pipeline for views, storage, validation, and MIME.

        Returns
        -------
        None
            Initialize built-in factories and an empty immutable fluent chain.
        """
        self._app = app
        self._composer = composer
        self._factories: dict[str, TransportFactory] = {
            "smtp": create_smtp_transport,
            "file": create_file_transport,
        }
        super().__init__(self._deliver)

    def extend(self, driver: str, factory: TransportFactory) -> None:
        """
        Register a new driver without silently replacing existing registrations.

        Parameters
        ----------
        driver : str
            Unique implementation name used in a mailer's driver option.
        factory : TransportFactory
            Callable receiving the application and the normalized configuration
            and returning an IMailTransport or an awaitable of one.

        Returns
        -------
        None
            Store the factory without running it or validating mailer entries.

        Raises
        ------
        MailConfigurationException
            If registration is invalid or duplicates a built-in or custom driver.
        """
        if not isinstance(driver, str) or not driver.strip() or not callable(factory):
            error_msg = "extend() requires a non-empty driver and a callable factory."
            raise MailConfigurationException(error_msg)
        if driver in self._factories:
            error_msg = f"Mail driver [{driver}] is already registered."
            raise MailConfigurationException(error_msg)
        self._factories[driver] = factory

    async def _deliver(
        self,
        name: str | None,
        envelope: Envelope,
        content: Content,
        attachments: tuple[Attachment, ...],
    ) -> MailResult:
        """
        Prepare a message completely before resolving and invoking its transport.

        Parameters
        ----------
        name : str | None
            Explicit mailer name, or None for the central default.
        envelope : Envelope
            Final operation-local envelope.
        content : Content
            Normalized content declaration.
        attachments : tuple[Attachment, ...]
            Merged deferred attachments.

        Returns
        -------
        MailResult
            Result reported by the selected transport.

        Raises
        ------
        MailConfigurationException
            If the mailer, driver, or factory result is invalid.
        MailException
            If composition, rendering, attachment resolution, or transport fails.
        """
        mailer, driver, config = self._resolveMailer(name)
        factory = self._factories.get(driver)
        if factory is None:
            error_msg = f"Mail driver [{driver}] has no registered implementation."
            raise MailConfigurationException(error_msg)

        # Only messages without an explicit sender read the global setting.
        if envelope.from_address is None:
            envelope = self._applyGlobalSender(envelope)

        # Preparation runs first so a rendering or attachment failure never
        # opens a connection or publishes a file.
        prepared = await self._composer.prepare(envelope, content, attachments)

        transport = factory(self._app, config)
        if isawaitable(transport):
            transport = await transport
        if not isinstance(transport, IMailTransport):
            error_msg = "Mail driver factories must return an IMailTransport."
            raise MailConfigurationException(error_msg)
        return await transport.send(prepared, mailer=mailer, driver=driver)

    def _applyGlobalSender(self, envelope: Envelope) -> Envelope:
        """
        Overlay the configured global sender on an envelope that declares none.

        Parameters
        ----------
        envelope : Envelope
            Operation-local envelope without a From header.

        Returns
        -------
        Envelope
            The received envelope when no global sender is configured, or an
            equivalent copy carrying the configured mailbox.

        Raises
        ------
        MailConfigurationException
            If the configured sender is neither a mapping nor an entity.
        MailCompositionException
            If the configured mailbox or display name is invalid.
        """
        section = _configuration_mapping(self._app.config("mail"))
        declared = section.get("from_address")
        if declared is None:
            return envelope

        sender = _configuration_mapping(declared)
        address = sender.get("address", "")
        if not isinstance(address, str) or not address.strip():
            return envelope

        name = sender.get("name", "")
        display = name.strip() if isinstance(name, str) else ""
        return Envelope(
            subject=envelope.subject,
            from_address=Address(address.strip(), display or None),
            to=envelope.to,
            cc=envelope.cc,
            bcc=envelope.bcc,
            reply_to=envelope.reply_to,
        )

    def _resolveMailer(
        self,
        name: str | None,
    ) -> tuple[str, str, Mapping[str, object]]:
        """
        Normalize only the selected central mailer without environment reads.

        Parameters
        ----------
        name : str | None
            Explicit mailer, or None for the central default.

        Returns
        -------
        tuple[str, str, Mapping[str, object]]
            Mailer name, driver name, and copied read-only configuration.

        Raises
        ------
        MailConfigurationException
            If the section, name, or selected entry is invalid or missing.
        """
        section = _configuration_mapping(self._app.config("mail"))
        mailer = section.get("default") if name is None else name
        if not isinstance(mailer, str) or not mailer.strip():
            error_msg = "The mail section requires a non-empty default mailer."
            raise MailConfigurationException(error_msg)

        entries = _configuration_mapping(section.get("mailers"))
        if mailer not in entries:
            error_msg = f"Mailer [{mailer}] is not defined in the mail configuration."
            raise MailConfigurationException(error_msg)

        # Conventional smtp and file entries may omit their driver name.
        settings = _configuration_mapping(entries[mailer])
        inferred = mailer if mailer in _CONVENTIONAL_DRIVERS else None
        driver = settings.get("driver", inferred)
        if not isinstance(driver, str) or not driver.strip():
            error_msg = f"Mailer [{mailer}] requires an explicit driver."
            raise MailConfigurationException(error_msg)

        normalized = freeze_owned({**settings, "driver": driver})
        return mailer, driver, cast("Mapping[str, object]", normalized)

def _configuration_mapping(value: object) -> dict[str, object]:
    """
    Copy one configuration layer while preserving arbitrary dependency values.

    Parameters
    ----------
    value : object
        Central dictionary, immutable mapping, or configuration entity.

    Returns
    -------
    dict[str, object]
        Fresh mapping built without invoking environment-backed constructors.

    Raises
    ------
    MailConfigurationException
        If the configuration is neither a mapping nor an entity.
    """
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, BaseEntity) and is_dataclass(value):
        return {item.name: getattr(value, item.name) for item in fields(value)}
    error_msg = "Mail configuration requires mappings or mail configuration entities."
    raise MailConfigurationException(error_msg)
