"""Publish complete private .eml files atomically without overwriting."""

import os
import secrets
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING
from orionis.aio import Loop
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.entities.result import MailResult
from orionis.mail.enums.status import MailStatus
from orionis.mail.exceptions import MailConfigurationException, MailTransportException

if TYPE_CHECKING:
    from collections.abc import Mapping
    from orionis.foundation.contracts.application import IApplication
    from orionis.mail.entities.prepared import PreparedMail

_DEFAULT_OUTPUT_PATH = "storage/mail"
"""Default output path identifier: ``storage/mail``."""
_DIRECTORY_MODE = 0o700
"""Directory mode value used by ``file``."""

class FileTransport(IMailTransport):
    """
    Publish complete private .eml files atomically without overwriting.

    Publication requires hard-link support in the target filesystem, such as
    NTFS on Windows or a regular local POSIX filesystem; unsupported
    filesystems fail explicitly. Each worker owns its temporary file and
    never shares per-message state.
    """

    __slots__ = ("_path",)
    """Declare the instance attribute slots reserved by this class."""

    def __init__(self, path: Path) -> None:
        """
        Retain the application-rooted output directory without touching disk.

        Parameters
        ----------
        path : pathlib.Path
            Absolute output directory, already anchored by the factory.

        Returns
        -------
        None
            Store only transport configuration.
        """
        self._path = path
        """Absolute output directory, already anchored by the factory."""

    async def send(
        self,
        message: PreparedMail,
        *,
        mailer: str,
        driver: str,
    ) -> MailResult:
        """
        Write and atomically publish one complete message on a worker.

        Parameters
        ----------
        message : orionis.mail.entities.PreparedMail
            Complete MIME bytes and intended recipients.
        mailer : str
            Selected configuration name.
        driver : str
            Registered driver name.

        Returns
        -------
        orionis.mail.entities.MailResult
            Stored result with the final path and no SMTP acceptance claims.

        Raises
        ------
        orionis.mail.exceptions.MailTransportException
            If writing, syncing, or atomic publication fails.
        """
        try:
            path = await Loop.execute(self._store, message.mime)
        except OSError as exc:
            error_msg = "Unable to publish the mail file atomically."
            raise MailTransportException(error_msg) from exc

        return MailResult(
            message_id=message.message_id,
            mailer=mailer,
            driver=driver,
            status=MailStatus.STORED,
            recipients=message.recipients,
            file_path=path,
        )

    def _store(self, payload: bytes) -> Path:
        """
        Stage, sync, and link a message without exposing partial final files.

        Parameters
        ----------
        payload : bytes
            Serialized MIME message.

        Returns
        -------
        pathlib.Path
            Absolute uniquely named final file.

        Raises
        ------
        OSError
            If any filesystem operation fails; existing files stay untouched.
        """
        self._path.mkdir(mode=_DIRECTORY_MODE, parents=True, exist_ok=True)
        final = self._path / f"{secrets.token_hex(16)}.eml"
        temporary: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="wb",
                prefix=".orionis-mail-",
                suffix=".tmp",
                dir=self._path,
                delete=False,
            ) as stream:
                temporary = Path(stream.name)
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())

            # Linking fails instead of overwriting when the name already
            # exists, so a published message is never replaced.
            os.link(temporary, final)
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError as cleanup_error:
                    from orionis.failure.runtime import capture_nowait  # noqa: PLC0415
                    capture_nowait(
                        cleanup_error,
                        flow="mail",
                        phase="cleanup",
                        operation="file.publish",
                    )
        return final

def create_file_transport(
    app: IApplication,
    config: Mapping[str, object],
) -> IMailTransport:
    """
    Build a file transport anchored to the application, never the process cwd.

    Parameters
    ----------
    app : orionis.IApplication
        Container exposing the absolute application root.
    config : collections.abc.Mapping[str, object]
        Normalized selected mailer configuration.

    Returns
    -------
    orionis.mail.contracts.IMailTransport
        A transport that creates no files until a message is sent.

    Raises
    ------
    orionis.mail.exceptions.MailConfigurationException
        If the configured output path is empty, invalid, or drive-relative.
    """
    raw = config.get("path", _DEFAULT_OUTPUT_PATH)
    if not isinstance(raw, (str, Path)) or not str(raw).strip() or "\x00" in str(raw):
        error_msg = "The file mailer requires a valid non-empty output path."
        raise MailConfigurationException(error_msg)

    path = Path(raw)
    if not path.is_absolute():

        # A Windows drive-relative or root-relative path has an anchor but no
        # drive, so it cannot be resolved against the application root.
        if path.anchor:
            error_msg = "File mailer paths must be absolute or application-relative."
            raise MailConfigurationException(error_msg)
        path = app.basePath / path
    return FileTransport(path)
