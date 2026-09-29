import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, Self
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.entities.result import MailResult
from orionis.mail.enums.status import MailStatus
from orionis.storage.disk import Disk
from orionis.storage.drivers.memory import MemoryStorageDriver
from orionis.storage.exceptions import UnsupportedStorageOperationException

if TYPE_CHECKING:
    from orionis.mail.entities.attachment import Attachment
    from orionis.mail.entities.content import Content
    from orionis.mail.entities.envelope import Envelope
    from orionis.mail.entities.prepared import PreparedMail

_FIXTURE_ROOT = Path(__file__).parent

class ViewApplication:
    """Expose explicit view configuration without an HTTP request."""

    __slots__ = ("base_path",)

    def __init__(self, path: Path) -> None:
        """Initialize the test helper.

        Parameters
        ----------
        path : Path
            Value supplied for ``path``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.base_path = path

    @property
    def basePath(self) -> Path:
        """Return the application root required by ViewEnvironment.

        Returns
        -------
        Path
            Value produced by the helper.
        """
        return self.base_path

    def config(self, key: str) -> object:
        """Return the fixture template directory as the configured loader.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.

        Returns
        -------
        object
            Value produced by the helper.

        Raises
        ------
        KeyError
            Raised by this helper to exercise the failure path.
        """
        if key != "view":
            error_msg = "Unexpected configuration section."
            raise KeyError(error_msg)
        return {
            "paths": [str(_FIXTURE_ROOT)],
            "cache_path": None,
            "autoescape": True,
        }

class MailApplication(ViewApplication):
    """Expose central mail configuration plus a recording dependency resolver."""

    __slots__ = ("mail_config", "resolved")

    def __init__(self, path: Path, config: object) -> None:
        """Initialize the test helper.

        Parameters
        ----------
        path : Path
            Value supplied for ``path``.
        config : object
            Value supplied for ``config``.

        Returns
        -------
        None
            Completes the operation described above.
        """
        super().__init__(path)
        self.mail_config = config
        self.resolved: list[type] = []

    def config(self, key: str) -> object:
        """Serve the selected section without reading environment variables.

        Parameters
        ----------
        key : str
            Value supplied for ``key``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        return self.mail_config if key == "mail" else super().config(key)

    async def make(self, contract: type) -> object:
        """Resolve the dependency requested by an extension factory.

        Parameters
        ----------
        contract : type
            Value supplied for ``contract``.

        Returns
        -------
        object
            Value produced by the helper.
        """
        self.resolved.append(contract)
        return contract()

class RenderingEngine:
    """Return a controlled render result instead of a real template."""

    __slots__ = ("failure", "rendered", "requested")

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.failure: Exception | None = None
        self.rendered: object = "rendered"
        self.requested: list[tuple[str, dict[str, object]]] = []

    async def render(self, template: str, data: dict[str, object]) -> object:
        """Record the request and return the configured render result.

        Parameters
        ----------
        template : str
            Value supplied for ``template``.
        data : dict[str, object]
            Value supplied for ``data``.

        Returns
        -------
        object
            Value produced by the helper.

        Raises
        ------
        self.failure
            Raised by this helper to exercise the failure path.
        """
        self.requested.append((template, data))
        if self.failure is not None:
            raise self.failure
        return self.rendered

class MemoryStorage:
    """Expose memory-backed disks without local paths or public URLs."""

    __slots__ = ("default_disk", "disks", "selected")

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.disks = {
            "local": Disk("local", MemoryStorageDriver()),
            "remote": Disk("remote", MemoryStorageDriver()),
        }
        self.default_disk = "remote"
        self.selected: list[str | None] = []

    def disk(self, name: str | None = None) -> Disk:
        """Resolve an explicit or default disk and record the selection.

        Parameters
        ----------
        name : str | None
            Value supplied for ``name``.

        Returns
        -------
        Disk
            Value produced by the helper.
        """
        self.selected.append(name)
        return self.disks[name or self.default_disk]

class RemoteStream:
    """Expose an async stream without any local filesystem handle or path."""

    __slots__ = (
        "close_error",
        "closed",
        "entered",
        "open_error",
        "payload",
        "read_error",
        "release",
    )

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.close_error = False
        self.closed = 0
        self.entered = asyncio.Event()
        self.open_error = False
        self.payload: object = b"remote-data"
        self.read_error = False
        self.release = asyncio.Event()
        self.release.set()

    async def __aenter__(self) -> Self:
        """Pause opening when requested to exercise cancellation-safe ownership.

        Returns
        -------
        Self
            Value produced by the helper.

        Raises
        ------
        PermissionError
            Raised by this helper to exercise the failure path.
        """
        self.entered.set()
        await self.release.wait()
        if self.open_error:
            error_msg = "Remote opening denied."
            raise PermissionError(error_msg)
        return self

    async def read(self) -> object:
        """Return bytes or an explicit simulated driver failure value.

        Returns
        -------
        object
            Value produced by the helper.

        Raises
        ------
        PermissionError
            Raised by this helper to exercise the failure path.
        """
        if self.read_error:
            error_msg = "Remote read denied."
            raise PermissionError(error_msg)
        return self.payload

    async def close(self) -> None:
        """Record stream cleanup, including on read errors.

        Returns
        -------
        None
            Completes the operation described above.

        Raises
        ------
        OSError
            Raised by this helper to exercise the failure path.
        """
        self.closed += 1
        if self.close_error:
            error_msg = "Remote close failed."
            raise OSError(error_msg)

class RemoteStorage:
    """Serve the real disk/file/stream call shape without a local path."""

    __slots__ = ("metadata_calls", "mime_type", "paths", "selected", "stream")

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.metadata_calls = 0
        self.mime_type: str | None = None
        self.paths: list[str] = []
        self.selected: list[str | None] = []
        self.stream = RemoteStream()

    def disk(self, name: str | None = None) -> Self:
        """Record the explicit or default disk selected by preparation.

        Parameters
        ----------
        name : str | None
            Value supplied for ``name``.

        Returns
        -------
        Self
            Value produced by the helper.
        """
        self.selected.append(name)
        return self

    def file(self, path: str) -> Self:
        """Record the normalized logical path without rebuilding a local path.

        Parameters
        ----------
        path : str
            Value supplied for ``path``.

        Returns
        -------
        Self
            Value produced by the helper.
        """
        self.paths.append(path)
        return self

    async def mimeType(self) -> str | None:
        """Return backend metadata or a supported metadata-absent signal.

        Returns
        -------
        str | None
            Value produced by the helper.

        Raises
        ------
        UnsupportedStorageOperationException
            Raised by this helper to exercise the failure path.
        """
        self.metadata_calls += 1
        if self.mime_type == "unsupported":
            error_msg = "Metadata unsupported."
            raise UnsupportedStorageOperationException(error_msg)
        return self.mime_type

    def open(self, mode: str) -> RemoteStream:
        """Return a lazily opened stream with no filesystem representation.

        Parameters
        ----------
        mode : str
            Value supplied for ``mode``.

        Returns
        -------
        RemoteStream
            Value produced by the helper.

        Raises
        ------
        ValueError
            Raised by this helper to exercise the failure path.
        """
        if mode != "rb":
            error_msg = "Expected binary read mode."
            raise ValueError(error_msg)
        return self.stream

class RecordingDelivery:
    """Capture the declarations a chain hands to the delivery pipeline."""

    __slots__ = ("messages",)

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.messages: list[
            tuple[str | None, Envelope, Content, tuple[Attachment, ...]]
        ] = []

    async def __call__(
        self,
        mailer: str | None,
        envelope: Envelope,
        content: Content,
        attachments: tuple[Attachment, ...],
    ) -> MailResult:
        """Record one declaration without opening a production transport.

        Parameters
        ----------
        mailer : str | None
            Value supplied for ``mailer``.
        envelope : Envelope
            Value supplied for ``envelope``.
        content : Content
            Value supplied for ``content``.
        attachments : tuple[Attachment, ...]
            Value supplied for ``attachments``.

        Returns
        -------
        MailResult
            Value produced by the helper.
        """
        self.messages.append((mailer, envelope, content, attachments))
        await asyncio.sleep(0)
        return MailResult(
            message_id="<test@example.com>",
            mailer=mailer or "file",
            driver="file",
            status=MailStatus.STORED,
            recipients=envelope.recipients(),
        )

class RecordingTransport(IMailTransport):
    """Record only prepared mail; never see templates or logical paths."""

    __slots__ = ("messages",)

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.messages: list[PreparedMail] = []

    async def send(
        self,
        message: PreparedMail,
        *,
        mailer: str,
        driver: str,
    ) -> MailResult:
        """Record one message and return a typed test-only storage result.

        Parameters
        ----------
        message : PreparedMail
            Value supplied for ``message``.
        mailer : str
            Value supplied for ``mailer``.
        driver : str
            Value supplied for ``driver``.

        Returns
        -------
        MailResult
            Value produced by the helper.
        """
        self.messages.append(message)
        return MailResult(
            message_id=message.message_id,
            mailer=mailer,
            driver=driver,
            status=MailStatus.STORED,
            recipients=message.recipients,
        )

class RecordingFactory:
    """Exercise the public extension signature and async dependency lookup."""

    __slots__ = ("configs", "transports")

    def __init__(self) -> None:
        """Initialize the test helper.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.configs: list[object] = []
        self.transports: list[RecordingTransport] = []

    async def __call__(self, app: object, config: object) -> IMailTransport:
        """Obtain a transport dependency through the supplied container.

        Parameters
        ----------
        app : object
            Value supplied for ``app``.
        config : object
            Value supplied for ``config``.

        Returns
        -------
        IMailTransport
            Value produced by the helper.
        """
        self.configs.append(config)
        transport = await app.make(RecordingTransport)
        self.transports.append(transport)
        return transport
