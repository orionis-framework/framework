from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.http.payload.uploaded_file import UploadedFile
from orionis.test import TestCase


class TestUploadedFileAppend(TestCase):
    """Preserve uploaded content when writes follow partial reads."""

    def testWriteAppendsAfterPartialReadsAcrossSpoolStates(self) -> None:
        """Append in memory, during rollover and after spilling to disk."""
        for threshold in (0, 1024, 6, 1):
            for chunk in (b"XYZ", bytearray(b"XYZ"), memoryview(b"XYZ")):
                with closing(UploadedFile(
                    "sample.txt", "text/plain", memory_threshold=threshold,
                )) as upload:
                    upload.write(b"abcdef")
                    self.assertEqual(upload.requiresDiskWrite(), threshold == 1)
                    with closing(upload.chunks(2)) as reader:
                        self.assertEqual(next(reader), b"ab")
                    self.assertEqual(
                        upload.requiresDiskWrite(len(chunk)), threshold in (1, 6),
                    )
                    upload.write(chunk)
                    self.assertEqual(upload.read(), b"abcdefXYZ")
                    self.assertEqual(upload.size, 9)
                    self.assertEqual(upload.requiresDiskWrite(), threshold in (1, 6))
                    self.assertEqual(b"".join(upload.chunks(2)), b"abcdefXYZ")

    def testWriteAppendsAfterReplacingAndSavingContent(self) -> None:
        """Keep replacement size and saved bytes consistent after partial reads."""
        for threshold in (0, 1):
            with TemporaryDirectory() as directory, closing(UploadedFile(
                "sample.txt", "text/plain", memory_threshold=threshold,
            )) as upload:
                upload.write(b"original content")
                upload.replace(b"12345")
                with closing(upload.chunks(1)) as reader:
                    self.assertEqual(next(reader), b"1")
                upload.write(b"")
                self.assertEqual(upload.size, 5)
                self.assertEqual(upload.read(), b"12345")
                with closing(upload.chunks(2)) as reader:
                    self.assertEqual(next(reader), b"12")
                upload.write(b"67")
                destination = Path(directory) / "saved.txt"
                upload.save(destination)
                self.assertEqual(destination.read_bytes(), b"1234567")
                self.assertEqual(upload.read(), b"1234567")
                self.assertEqual(upload.size, 7)
