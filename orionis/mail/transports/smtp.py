import smtplib
import ssl
from contextlib import suppress
from typing import TYPE_CHECKING
from orionis.aio import Loop
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.entities.result import MailResult
from orionis.mail.entities.smtp_settings import SmtpSettings
from orionis.mail.enums.encryption import MailEncryption
from orionis.mail.enums.status import MailStatus
from orionis.mail.exceptions import MailTransportException
from orionis.mail.functions import sanitize_reason

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.foundation.contracts.application import IApplication
    from orionis.mail.entities.prepared import PreparedMail

_SMTP_READY = 220

class SmtpTransport(IMailTransport):
    """
    Use one verified SMTP connection per message, entirely on a worker.

    Cancelling the awaiting task does not stop the worker and does not prove
    that the server refused the message. There are no automatic retries.
    """

    __slots__ = ("_settings",)

    def __init__(self, settings: SmtpSettings) -> None:
        """
        Retain validated settings without opening a connection.

        Parameters
        ----------
        settings : SmtpSettings
            Immutable effective connection options.

        Returns
        -------
        None
            Store transport configuration only.
        """
        self._settings = settings

    async def send(
        self,
        message: PreparedMail,
        *,
        mailer: str,
        driver: str,
    ) -> MailResult:
        """
        Run the complete blocking SMTP cycle outside the event loop.

        Parameters
        ----------
        message : PreparedMail
            Already materialized MIME and a validated separate envelope.
        mailer : str
            Configuration name reported in the result.
        driver : str
            Registered transport name reported in the result.

        Returns
        -------
        MailResult
            Total or partial acceptance confirmed by the SMTP transaction.

        Raises
        ------
        MailTransportException
            If the transaction fails or every recipient is rejected.
        """
        return await Loop.execute(self._sendSync, message, mailer, driver)

    def _sendSync(
        self,
        message: PreparedMail,
        mailer: str,
        driver: str,
    ) -> MailResult:
        """
        Connect, negotiate, authenticate, transmit, and always close.

        Parameters
        ----------
        message : PreparedMail
            Complete operation-local message.
        mailer : str
            Selected configuration name.
        driver : str
            Registered driver name.

        Returns
        -------
        MailResult
            Confirmed recipient acceptance after a successful transaction.

        Raises
        ------
        MailTransportException
            Sanitized failure identifying stage, exception type, and SMTP code.
        """
        settings = self._settings
        client: smtplib.SMTP | None = None
        stage = "connection"
        try:
            client = (
                smtplib.SMTP_SSL(
                    timeout=settings.timeout,  # type: ignore[arg-type]
                    context=_tls_context(),
                )
                if settings.encryption is MailEncryption.SSL
                else smtplib.SMTP(
                    timeout=settings.timeout,  # type: ignore[arg-type]
                )
            )
            code, reply = client.connect(settings.host, settings.port)
            if code != _SMTP_READY:
                raise smtplib.SMTPConnectError(code, reply)
            client.ehlo_or_helo_if_needed()

            # A failed or unavailable upgrade aborts the operation: plaintext
            # is only used when it was requested explicitly.
            if settings.encryption is MailEncryption.TLS:
                stage = "STARTTLS"
                client.starttls(context=_tls_context())
                client.ehlo_or_helo_if_needed()

            if settings.username:
                stage = "authentication"
                client.login(settings.username, settings.password)

            stage = "SMTPUTF8 negotiation"
            options = _mail_options(client, message)

            stage = "message transaction"
            refused = client.sendmail(
                message.sender,
                message.recipients,
                message.mime,
                mail_options=options,
            )
            return self._result(message, mailer, driver, refused)
        except (OSError, ValueError) as exc:
            code = None
            if isinstance(exc, smtplib.SMTPResponseException):
                code = exc.smtp_code
            detail = f"{type(exc).__name__}" + (f", code {code}" if code else "")
            error_msg = (
                f"SMTP failed during {stage} ({detail}). "
                "The server may have accepted the message; no retry was attempted."
            )

            # The original exception is suppressed because its payload can
            # carry credentials or private server responses.
            raise MailTransportException(error_msg) from None
        finally:
            if client is not None:
                with suppress(OSError):
                    client.close()

    def _result(
        self,
        message: PreparedMail,
        mailer: str,
        driver: str,
        refused: Mapping[str, tuple[int, bytes | str]],
    ) -> MailResult:
        """
        Report exactly the recipients accepted by a completed transaction.

        Parameters
        ----------
        message : PreparedMail
            Intended recipient union and message identifier.
        mailer : str
            Selected configuration name.
        driver : str
            Registered driver name.
        refused : Mapping[str, tuple[int, bytes | str]]
            Recipient rejections returned after the transaction succeeded.

        Returns
        -------
        MailResult
            Accepted or partial, with sanitized immutable rejection metadata.

        Raises
        ------
        MailTransportException
            If no recipient was accepted.
        """
        accepted = tuple(
            address for address in message.recipients if address not in refused
        )
        if not accepted:
            error_msg = "SMTP rejected all recipients."
            raise MailTransportException(error_msg)

        rejected = {
            address: (code, sanitize_reason(reason, self._settings.sensitive))
            for address, (code, reason) in refused.items()
        }
        return MailResult(
            message_id=message.message_id,
            mailer=mailer,
            driver=driver,
            status=MailStatus.PARTIAL if rejected else MailStatus.ACCEPTED,
            recipients=message.recipients,
            accepted_recipients=accepted,
            rejected_recipients=rejected,
        )

def _mail_options(client: smtplib.SMTP, message: PreparedMail) -> list[str]:
    """
    Require advertised SMTPUTF8 support for international mailbox addresses.

    Parameters
    ----------
    client : smtplib.SMTP
        Connection after EHLO and any required TLS negotiation.
    message : PreparedMail
        Prepared message with its UTF-8 requirement.

    Returns
    -------
    list[str]
        Explicit MAIL FROM extensions, empty for ASCII mailboxes.

    Raises
    ------
    MailTransportException
        If an international mailbox cannot be transmitted without loss.
    """
    if not message.smtp_utf8:
        return []

    if not client.has_extn("smtputf8") or not client.has_extn("8bitmime"):
        error_msg = "SMTPUTF8 and 8BITMIME are required for international mailboxes."
        raise MailTransportException(error_msg)
    return ["SMTPUTF8", "BODY=8BITMIME"]

def _tls_context() -> ssl.SSLContext:
    """
    Require trusted certificates, hostname verification, and TLS 1.2 or newer.

    Returns
    -------
    ssl.SSLContext
        A client context using the system trust store.
    """
    context = ssl.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl.CERT_REQUIRED
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context

def create_smtp_transport(
    app: IApplication,  # noqa: ARG001
    config: Mapping[str, object],
) -> IMailTransport:
    """
    Build SMTP from the central configuration without network activity.

    Parameters
    ----------
    app : IApplication
        Container supplied uniformly to every transport factory.
    config : Mapping[str, object]
        Normalized selected mailer settings.

    Returns
    -------
    IMailTransport
        Configured connection-per-message SMTP transport.

    Raises
    ------
    MailConfigurationException
        If the effective SMTP settings are invalid.
    """
    return SmtpTransport(SmtpSettings.fromConfig(config))
