from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from orionis.http.responses import FileResponse, Response, StreamingResponse
from orionis.test import TestCase
from tests.http._support import replace_attribute

if TYPE_CHECKING:
    from os import stat_result

class _BodyBytes(bytes):
    __slots__ = ()

class TestResponseResources(TestCase):

    def testFileConstructionUsesOneStat(self) -> None:
        """Read file type and size from the same metadata result."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "file.txt"
            path.write_bytes(b"data")
            stat = Path.stat
            calls = []

            def record_stat(
                file_path: Path, *, follow_symlinks: bool = True,
            ) -> stat_result:
                """
                Record the metadata lookup and return the actual file status.

                Parameters
                ----------
                file_path : Path
                    Path of the file to inspect or open.
                follow_symlinks : bool
                    Whether metadata follows symbolic links.

                Returns
                -------
                stat_result
                    Metadata returned by the filesystem.
                """
                calls.append(file_path)
                return stat(file_path, follow_symlinks=follow_symlinks)

            with replace_attribute(Path, "stat", record_stat):
                response = FileResponse(path, media_type="text/plain")
            self.assertEqual(calls, [path])
            self.assertEqual(response.getFileSize(), 4)

    def testFileRejectsInvalidChunkSizes(self) -> None:
        """Reject chunk sizes that cannot produce a bounded byte stream."""
        with TemporaryDirectory() as directory:
            path = Path(directory) / "file.txt"
            path.write_bytes(b"data")
            for chunk_size in (0, -1):
                with self.subTest(chunk_size=chunk_size), self.assertRaises(ValueError):
                    FileResponse(path, chunk_size=chunk_size)
            with self.assertRaises(TypeError):
                FileResponse(path, chunk_size="invalid")

    def testBytesSubclassIsPreserved(self) -> None:
        """Treat byte subclasses as encoded response bodies."""
        content = _BodyBytes(b"raw")
        self.assertIs(Response(content).getBody(), content)

    async def testSyncStreamAcceptsBytesSubclasses(self) -> None:
        """Preserve byte subclass chunks in synchronous streams."""
        content = _BodyBytes(b"raw")
        response = StreamingResponse([content])
        chunks = [chunk async for chunk in response.getStream()]
        self.assertIs(chunks[0], content)
