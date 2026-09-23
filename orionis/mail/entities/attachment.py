from dataclasses import dataclass
from typing import Self
from orionis.mail.exceptions import MailAttachmentException, MailCompositionException
from orionis.mail.functions import attachment_name, header_value, media_type
from orionis.storage.exceptions import StoragePathException
from orionis.storage.paths import normalizeFilePath

@dataclass(frozen=True, slots=True, kw_only=True)
class Attachment:
    """
    Describe a storage attachment without opening it or resolving a disk.

    Parameters
    ----------
    path : str
        Logical disk-relative path, normalized on declaration.
    disk : str | None
        Configured disk name, or None for the default disk.
    name : str | None
        Visible basename overriding the logical path's basename.
    mime_type : str | None
        Explicit MIME type overriding storage metadata and inference.
    """

    path: str
    disk: str | None = None
    name: str | None = None
    mime_type: str | None = None

    def __post_init__(self) -> None:
        """
        Validate logical paths and safe optional metadata without I/O.

        Returns
        -------
        None
            Store canonical paths and MIME types.

        Raises
        ------
        MailAttachmentException
            If a path, disk name, visible name, or MIME type is unsafe.
        """
        try:
            header_value(self.path, "Attachment path")
            object.__setattr__(self, "path", normalizeFilePath(self.path))
            if self.disk is not None and not header_value(self.disk, "Disk").strip():
                error_msg = "Attachment disk names must not be empty."
                raise MailAttachmentException(error_msg)
        except (StoragePathException, MailCompositionException) as exc:
            error_msg = "Invalid storage attachment path or disk."
            raise MailAttachmentException(error_msg) from exc

        if self.name is not None:
            attachment_name(self.name)
        if self.mime_type is not None:
            object.__setattr__(self, "mime_type", media_type(self.mime_type))

    @classmethod
    def fromStorage(
        cls,
        path: str,
        *,
        disk: str | None = None,
        name: str | None = None,
        mime_type: str | None = None,
    ) -> Self:
        """
        Declare a file to resolve through Orionis storage when sending.

        Parameters
        ----------
        path : str
            Logical disk-relative path.
        disk : str | None
            Configured disk name, or None for the default disk.
        name : str | None
            Visible basename overriding the logical path's basename.
        mime_type : str | None
            Explicit MIME type overriding storage metadata and inference.

        Returns
        -------
        Self
            An immutable attachment declaration, with no I/O performed.

        Raises
        ------
        MailAttachmentException
            If the declaration contains unsafe paths or metadata.
        """
        return cls(path=path, disk=disk, name=name, mime_type=mime_type)
