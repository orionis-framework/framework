from __future__ import annotations
import base64
import quopri
from contextlib import suppress
from typing import TYPE_CHECKING
from urllib.parse import unquote_to_bytes
from orionis.http.payload.contracts.part import IMultipartPart
from orionis.http.payload.uploaded_file import UploadedFile

if TYPE_CHECKING:
    from collections.abc import Callable

class MultipartPart(IMultipartPart):
    """Represent a single part within a multipart HTTP request body."""

    __slots__ = (
        "_write",
        "content_type",
        "data",
        "filename",
        "headers",
        "is_file",
        "name",
    )

    def __init__(
        self,
        headers: dict[str, str],
        memory_threshold: int,
    ) -> None:
        """
        Initialize a new ``MultipartPart`` from its MIME headers.

        Parameters
        ----------
        headers : dict[str, str]
            Lowercased headers for this multipart part.
        memory_threshold : int
            Maximum in-memory bytes before spilling to disk.

        Returns
        -------
        None
            Configures instance attributes; no value is returned.
        """
        # Store raw headers for later CTE and charset lookups
        self.headers = headers

        # Parse Content-Disposition to extract name, filename, and attrs.
        # _parseContentDisposition fuses RFC 5987 extended values (filename*)
        # over plain fallbacks, so attrs["filename"] is always the
        # highest-priority value when both forms are present.
        disposition = headers.get("content-disposition", "")
        attrs = self._parseContentDisposition(disposition)

        # Assign field metadata extracted from the disposition attributes
        self.name: str | None = attrs.get("name")
        self.filename: str | None = attrs.get("filename")
        self.content_type: str | None = headers.get("content-type")

        # A part is treated as a file upload when a filename is declared
        self.is_file: bool = self.filename is not None

        # Select the file or field buffer writer for this part.
        self.data: UploadedFile | bytearray
        self._write: Callable[[bytes | bytearray | memoryview], None]
        if self.is_file:
            # File parts accumulate bytes via a spill-aware UploadedFile
            self.data = UploadedFile(
                self.filename, self.content_type, memory_threshold,
            )
            self._write = self.data.write
        else:
            # Field parts accumulate raw bytes in an in-memory bytearray
            self.data = bytearray()
            self._write = self.data.extend

    def _parseContentDisposition(
        self,
        disposition: str,
    ) -> dict[str, str]:
        """
        Parse a ``Content-Disposition`` header into a key-value dict.

        Parameters
        ----------
        disposition : str
            Raw ``Content-Disposition`` header value.

        Returns
        -------
        dict[str, str]
            Lowercased attribute names mapped to unquoted values.
        """
        # Accumulate plain and RFC 5987 extended values in separate dicts
        attrs: dict[str, str] = {}
        # Extended values override plain fallbacks per RFC 6266 §4.1
        extended: dict[str, str] = {}

        for row_part in disposition.split(";"):
            part = row_part.strip()
            # Skip directive tokens that carry no value assignment
            if "=" not in part:
                continue

            # Split on first '=' only; values may themselves contain '='
            key, value = part.split("=", 1)
            key = key.strip().lower()
            value = value.strip()

            if key.endswith("*"):
                # RFC 5987 extended format: charset'language'pct-encoded
                plain_key = key[:-1]
                with suppress(Exception):  # NOSONAR
                    charset, _, tail = value.partition("'")
                    _, _, encoded = tail.partition("'")
                    decoded = unquote_to_bytes(encoded).decode(
                        charset.strip() or "utf-8",
                    )
                    extended[plain_key] = decoded
                continue

            # Strip surrounding single or double quotes from the value
            if (
                (value.startswith('"') and value.endswith('"'))
                or (value.startswith("'") and value.endswith("'"))
            ):
                value = value[1:-1]
            # Unescape embedded escaped-quote sequences
            value = value.replace('\\"', '"').replace("\\'", "'")
            attrs[key] = value

        # Merge: extended values win over same-named plain attributes
        attrs.update(extended)
        return attrs

    def write(self, chunk: bytes | bytearray | memoryview) -> None:
        """
        Append *chunk* to this part's data buffer.

        Parameters
        ----------
        chunk : bytes
            Raw bytes received from the multipart stream.

        Returns
        -------
        None
            Delegates to the pre-bound write callable; no value returned.
        """
        # Dispatch through the pre-bound callable set at construction time
        self._write(chunk)

    def finalize(self) -> UploadedFile | str:  # NOSONAR
        """
        Return this part's content in its final form.

        For field parts, applies ``Content-Transfer-Encoding`` decoding
        (``base64`` or ``quoted-printable``) and decodes to a string using
        the charset declared in the part's ``Content-Type`` header,
        falling back to UTF-8.

        Returns
        -------
        UploadedFile | str
            The ``UploadedFile`` handle for file parts, or the decoded
            string for field parts.
        """
        # Read the declared transfer encoding once for both code branches
        cte = (
            self.headers.get("content-transfer-encoding", "")
            .strip()
            .lower()
        )

        if not self.is_file:
            # Decode the field buffer using its declared transfer encoding.
            raw: bytes | bytearray = self.data  # type: ignore[assignment]
            # Apply CTE decoding when a transfer encoding is declared
            if cte == "base64":
                raw = base64.b64decode(raw)
            elif cte == "quoted-printable":
                raw = quopri.decodestring(raw)
            # Determine the target charset; fall back to UTF-8 per RFC 2045
            charset = "utf-8"
            content_type_hdr = self.headers.get("content-type", "")
            if content_type_hdr:
                # Extract the charset parameter from the Content-Type header.
                cs_idx = content_type_hdr.lower().find("charset=")
                if cs_idx != -1:
                    tail = content_type_hdr[cs_idx + 8:]
                    end = tail.find(";")
                    raw_val = tail[:end] if end != -1 else tail
                    val = raw_val.strip().strip('"').strip("'")
                    if val:
                        charset = val
            return raw.decode(charset)

        # File parts: decode CTE in-place when a transfer encoding is set
        if cte in ("base64", "quoted-printable"):
            file_obj: UploadedFile = self.data  # type: ignore[assignment]
            raw_encoded = file_obj.read()
            # Decode the full file content according to the declared CTE
            decoded = (
                base64.b64decode(raw_encoded)
                if cte == "base64"
                else quopri.decodestring(raw_encoded)
            )
            file_obj.replace(decoded)

        return self.data  # type: ignore[return-value]
