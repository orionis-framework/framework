import asyncio
from contextlib import suppress
from email import policy
from email.message import EmailMessage
from email.utils import format_datetime, make_msgid
from mimetypes import guess_type
from typing import TYPE_CHECKING
from orionis.aio import Loop
from orionis.mail.entities.attachment import Attachment
from orionis.mail.entities.prepared import PreparedMail
from orionis.mail.exceptions import MailAttachmentException, MailCompositionException
from orionis.mail.functions import attachment_name, media_type
from orionis.storage.contracts.manager import IStorageManager
from orionis.support.facades.datetime import DateTime
from orionis.storage.exceptions import UnsupportedStorageOperationException
from orionis.view.contracts.engine import IViewEngine

if TYPE_CHECKING:
    from orionis.mail.entities.content import Content
    from orionis.mail.entities.envelope import Envelope

# Attachment declaration paired with its payload and storage MIME metadata.
type LoadedAttachment = tuple[Attachment, bytes, str | None]

_DEFAULT_MEDIA_TYPE = "application/octet-stream"

class MailComposer:
    """
    Prepare all bodies and attachments before any transport side effect.

    The composer is shared and stateless: every operation keeps its envelope,
    rendered bodies, and attachment payloads in local variables.
    """

    # ruff: noqa: TC001

    __slots__ = ("_storage", "_view")

    def __init__(self, view: IViewEngine, storage: IStorageManager) -> None:
        """
        Inject the configured framework engines without using facades.

        Parameters
        ----------
        view : IViewEngine
            Existing text-rendering view engine.
        storage : IStorageManager
            Existing default/named disk resolver.

        Returns
        -------
        None
            Store only shared services, never operation state.
        """
        self._view = view
        self._storage = storage

    async def prepare(
        self,
        envelope: Envelope,
        content: Content,
        attachments: tuple[Attachment, ...],
    ) -> PreparedMail:
        """
        Validate, render, load attachments, and compose one immutable message.

        Parameters
        ----------
        envelope : Envelope
            Final merged headers and intended recipients.
        content : Content
            Validated literals or views with explicit context.
        attachments : tuple[Attachment, ...]
            Deferred storage declarations in attachment order.

        Returns
        -------
        PreparedMail
            Complete MIME bytes and transport envelope.

        Raises
        ------
        MailCompositionException
            If the envelope, view rendering, or MIME encoding fails.
        MailAttachmentException
            If any attachment cannot be read or has unsafe metadata.
        """
        if envelope.from_address is None:
            error_msg = "Mail requires a sender; use fromAddress() or Envelope."
            raise MailCompositionException(error_msg)
        if not envelope.recipients():
            error_msg = "Mail requires at least one To, Cc, or Bcc recipient."
            raise MailCompositionException(error_msg)

        text = await self._render(content.text_view, content.text, content)
        html = await self._render(content.view, content.html, content)
        loaded = [await self._resolveAttachment(item) for item in attachments]

        try:
            return await Loop.execute(
                self._compose,
                envelope,
                text,
                html,
                tuple(loaded),
            )
        except MailCompositionException:
            raise
        except (TypeError, ValueError) as exc:
            error_msg = "Unable to encode the mail MIME message."
            raise MailCompositionException(error_msg) from exc

    async def _render(
        self,
        template: str | None,
        literal: str | None,
        content: Content,
    ) -> str | None:
        """
        Render a view to text without constructing an HTTP response.

        Parameters
        ----------
        template : str | None
            Optional view identifier.
        literal : str | None
            Unchanged literal when no view was declared.
        content : Content
            Owner of the isolated explicit view context.

        Returns
        -------
        str | None
            Rendered text, literal text, or an undeclared body.

        Raises
        ------
        MailCompositionException
            If the configured view engine fails or does not return text.
        """
        if template is None:
            return literal

        try:
            rendered = await self._view.render(template, dict(content.data or {}))
        except Exception as exc:
            error_msg = "Mail view rendering failed before transport."
            raise MailCompositionException(error_msg) from exc

        if not isinstance(rendered, str):
            error_msg = "The mail view engine must return rendered text."
            raise MailCompositionException(error_msg)
        return rendered

    async def _resolveAttachment(self, attachment: Attachment) -> LoadedAttachment:
        """
        Own an attachment task until its stream is closed, even on cancellation.

        Parameters
        ----------
        attachment : Attachment
            Deferred storage declaration.

        Returns
        -------
        LoadedAttachment
            Declaration, binary data, and optional storage MIME type.

        Raises
        ------
        MailAttachmentException
            If storage fails to open, read, inspect, or close the attachment.
        asyncio.CancelledError
            After in-progress storage work finishes and releases its stream.
        """
        task = asyncio.create_task(self._readAttachment(attachment))
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            await _drain_attachment(task)
            raise
        except MailCompositionException:
            raise
        except Exception as exc:
            error_msg = "Unable to read a storage attachment before transport."
            raise MailAttachmentException(error_msg) from exc

    async def _readAttachment(self, attachment: Attachment) -> LoadedAttachment:
        """
        Read one backend-independent binary stream and close it reliably.

        Parameters
        ----------
        attachment : Attachment
            Logical path and optional metadata.

        Returns
        -------
        LoadedAttachment
            The full payload, including a valid zero-byte payload.

        Raises
        ------
        MailAttachmentException
            If a driver returns a non-binary failure value.
        Exception
            Propagate storage failures to the owning task for translation.
        """
        file = self._storage.disk(attachment.disk).file(attachment.path)

        # Backend metadata is optional: a disk may not expose MIME types.
        mime_type = attachment.mime_type
        if mime_type is None:
            with suppress(UnsupportedStorageOperationException):
                mime_type = await file.mimeType()
        if mime_type is not None:
            media_type(mime_type)

        stream = file.open("rb")
        try:
            await stream.__aenter__()
            payload = await stream.read()
        except BaseException:
            with suppress(Exception):
                await stream.close()
            raise
        else:
            await stream.close()

        if not isinstance(payload, bytes):
            error_msg = "Storage attachment reads must return bytes."
            raise MailAttachmentException(error_msg)
        return attachment, payload, mime_type

    @staticmethod
    def _compose(
        envelope: Envelope,
        text: str | None,
        html: str | None,
        attachments: tuple[LoadedAttachment, ...],
    ) -> PreparedMail:
        """
        Build and serialize MIME on a worker using the standard email library.

        Parameters
        ----------
        envelope : Envelope
            Validated final envelope.
        text : str | None
            Rendered or literal plain-text body.
        html : str | None
            Rendered or literal HTML body.
        attachments : tuple[LoadedAttachment, ...]
            Fully materialized storage attachments.

        Returns
        -------
        PreparedMail
            Message-ID, bytes without Bcc, and a separate recipient union.

        Raises
        ------
        MailCompositionException
            If the envelope carries no sender.
        """
        sender = envelope.from_address
        if sender is None:
            error_msg = "Cannot compose mail without a sender."
            raise MailCompositionException(error_msg)

        # Only a non-ASCII addr-spec requires SMTPUTF8; a Unicode display
        # name is encoded by the standard header policy.
        mailboxes = (
            sender,
            *envelope.to,
            *envelope.cc,
            *envelope.bcc,
            *envelope.reply_to,
        )
        smtp_utf8 = any(not address.address.isascii() for address in mailboxes)

        message = EmailMessage(policy=policy.SMTPUTF8 if smtp_utf8 else policy.SMTP)
        message_id = make_msgid(domain=sender.asHeader().domain)
        message["Date"] = format_datetime(DateTime.now())
        message["Message-ID"] = message_id
        message["From"] = sender.asHeader()
        message["Subject"] = envelope.subject

        # Bcc is deliberately absent: it only belongs to the transport envelope.
        for name, recipients in (
            ("To", envelope.to),
            ("Cc", envelope.cc),
            ("Reply-To", envelope.reply_to),
        ):
            if recipients:
                message[name] = tuple(address.asHeader() for address in recipients)

        if text is not None:
            message.set_content(text, subtype="plain", cte="quoted-printable")
            if html is not None:
                message.add_alternative(html, subtype="html", cte="quoted-printable")
        else:
            message.set_content(html, subtype="html", cte="quoted-printable")

        for declaration, payload, storage_type in attachments:
            name = attachment_name(
                declaration.name or declaration.path.rsplit("/", 1)[-1],
            )
            mime_type = media_type(
                declaration.mime_type
                or storage_type
                or guess_type(name)[0]
                or _DEFAULT_MEDIA_TYPE,
            )
            main_type, sub_type = mime_type.split("/")
            message.add_attachment(
                payload,
                maintype=main_type,
                subtype=sub_type,
                filename=name,
            )

        return PreparedMail(
            message_id=message_id,
            sender=sender.address,
            recipients=envelope.recipients(),
            mime=message.as_bytes(),
            smtp_utf8=smtp_utf8,
        )

async def _drain_attachment(task: asyncio.Task[LoadedAttachment]) -> None:
    """
    Finish owned storage cleanup while retaining the caller's cancellation.

    Parameters
    ----------
    task : asyncio.Task[LoadedAttachment]
        Shielded attachment task, possibly still opening a worker-owned stream.

    Returns
    -------
    None
        Observe the final task outcome without replacing cancellation.
    """
    completion = asyncio.gather(task, return_exceptions=True)
    while not completion.done():
        with suppress(asyncio.CancelledError):
            await asyncio.shield(completion)
