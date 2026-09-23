from contextlib import closing
from orionis.http.payload.parsers import parse_content_type
from orionis.http.payload.part import MultipartPart
from orionis.http.payload.uploaded_file import UploadedFile
from orionis.test import TestCase
from tests.http.test_request import make_asgi_request


class TestQuotedHeaderParameters(TestCase):
    """Preserve quoted delimiters across header and multipart parsing."""

    def testContentTypePreservesQuotedSemicolonsAndFollowingParameters(self) -> None:
        """Keep values intact without changing duplicate or escape handling."""
        cases = (
            (
                'TEXT/PLAIN; note = "alpha;beta=gamma"; Charset=UTF-8; empty=""; flag',
                {"note": "alpha;beta=gamma", "charset": "UTF-8", "empty": ""},
            ),
            (
                r'text/plain; note="alpha\";beta"; next=value',
                {"note": r'alpha\";beta', "next": "value"},
            ),
            (
                r'text/plain; note="alpha\\"; next=value',
                {"note": r"alpha\\", "next": "value"},
            ),
            (
                "text/plain; note=O'Brien; next=value; note=last",
                {"note": "last", "next": "value"},
            ),
            (
                'text/plain; note="alpha;beta; next=value',
                {"note": "alpha;beta; next=value"},
            ),
        )
        for header, expected in cases:
            self.assertEqual(parse_content_type(header), ("text/plain", expected))

    def testDispositionPreservesQuotedNamesAndFilenames(self) -> None:
        """Keep delimiters and escaped quotes inside both supported quote styles."""
        cases = (
            ('form-data; name="alpha;beta"; filename="a;b.txt"', "alpha;beta"),
            ("form-data; name='alpha;beta'; filename='a;b.txt'", "alpha;beta"),
            (r'form-data; name="alpha\";beta"; filename="a;b.txt"', 'alpha";beta'),
        )
        for disposition, expected_name in cases:
            part = MultipartPart({"content-disposition": disposition}, 1024)
            self.assertIsInstance(part.data, UploadedFile)
            with closing(part.data) as upload:
                self.assertEqual(part.name, expected_name)
                self.assertEqual(part.filename, "a;b.txt")
                self.assertEqual(upload.filename, "a;b.txt")
                self.assertEqual(upload.extension, ".txt")

    def testExtendedDispositionValuesRetainPriorityAndApostrophes(self) -> None:
        """Preserve extended decoding, plain fallbacks and unquoted apostrophes."""
        cases = (
            (
                (
                    "form-data; filename*=UTF-8''a%3Bb.txt; "
                    'filename="fallback;name.txt"; name="alpha;beta"'
                ),
                "a;b.txt",
                "alpha;beta",
            ),
            (
                (
                    'form-data; filename="fallback;name.txt"; '
                    "filename*=unknown''ignored; name=O'Brien"
                ),
                "fallback;name.txt",
                "O'Brien",
            ),
        )
        for disposition, expected_filename, expected_name in cases:
            part = MultipartPart({"content-disposition": disposition}, 1024)
            self.assertIsInstance(part.data, UploadedFile)
            with closing(part.data) as upload:
                self.assertEqual(part.filename, expected_filename)
                self.assertEqual(upload.filename, expected_filename)
                self.assertEqual(part.name, expected_name)

    async def testRequestFormPreservesQuotedParametersAndUploadedBytes(self) -> None:
        """Read quoted boundaries, field names and filenames through Request.form."""
        body = (
            b'--orionis;boundary\r\n'
            b'Content-Disposition: form-data; name="alpha;beta"\r\n\r\n'
            b'field value\r\n'
            b'--orionis;boundary\r\n'
            b'Content-Disposition: form-data; name="file;data"; filename="a;b.txt"\r\n'
            b'Content-Type: text/plain\r\n\r\n'
            b'uploaded content\r\n'
            b'--orionis;boundary--\r\n'
        )
        request = make_asgi_request(
            body=body,
            headers=[(
                b"content-type",
                b'multipart/form-data; boundary="orionis;boundary"; charset=UTF-8',
            )],
        )
        with await request.form() as form:
            self.assertEqual(form.get("alpha;beta"), "field value")
            upload = form.get("file;data")
            self.assertIsInstance(upload, UploadedFile)
            self.assertEqual(upload.filename, "a;b.txt")
            self.assertEqual(upload.read(), b"uploaded content")
            self.assertEqual(upload.size, len(b"uploaded content"))
