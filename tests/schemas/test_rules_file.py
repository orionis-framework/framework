import struct
from orionis.http.payload.uploaded_file import UploadedFile
from orionis.schemas.rules.dimensions import Dimensions
from orionis.schemas.rules.encoding import Encoding
from orionis.schemas.rules.file import File
from orionis.schemas.rules.image import Image
from orionis.schemas.rules.image_probe import probe_image
from orionis.schemas.rules.mime_types import MimeTypes
from orionis.schemas.rules.size import Size
from orionis.test import TestCase

# Shared owner instance; file rules never inspect sibling fields.
_OWNER = object()

def _png(width: int, height: int) -> bytes:
    """
    Build the header of a PNG carrying the given dimensions.

    Parameters
    ----------
    width : int
        Width stored in the ``IHDR`` chunk.
    height : int
        Height stored in the ``IHDR`` chunk.

    Returns
    -------
    bytes
        Signature and ``IHDR`` chunk of a synthetic PNG.
    """
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR"
        + struct.pack(">II", width, height)
        + b"\x08\x06\x00\x00\x00"
    )

def _gif(width: int, height: int) -> bytes:
    """
    Build the header of a GIF carrying the given dimensions.

    Parameters
    ----------
    width : int
        Width stored in the logical screen descriptor.
    height : int
        Height stored in the logical screen descriptor.

    Returns
    -------
    bytes
        Signature and logical screen descriptor of a synthetic GIF.
    """
    return b"GIF89a" + struct.pack("<HH", width, height) + b"\x00\x00\x00"

def _bmp(width: int, height: int) -> bytes:
    """
    Build the header of a bottom-up BMP carrying the given dimensions.

    Parameters
    ----------
    width : int
        Width stored in the information header.
    height : int
        Height stored in the information header, written as a negative
        value to exercise the bottom-up layout.

    Returns
    -------
    bytes
        File and information headers of a synthetic BMP.
    """
    return b"BM" + b"\x00" * 16 + struct.pack("<ii", width, -height)

def _jpeg(width: int, height: int) -> bytes:
    """
    Build the header of a JPEG carrying the given dimensions.

    Parameters
    ----------
    width : int
        Width stored in the start-of-frame segment.
    height : int
        Height stored in the start-of-frame segment.

    Returns
    -------
    bytes
        Signature, ``APP0`` segment and ``SOF0`` segment of a synthetic
        JPEG.
    """
    app0 = b"\xff\xe0" + struct.pack(">H", 16) + b"JFIF\x00" + b"\x00" * 9
    sof0 = (
        b"\xff\xc0"
        + struct.pack(">H", 17)
        + b"\x08"
        + struct.pack(">HH", height, width)
        + b"\x03"
        + b"\x00" * 9
    )
    return b"\xff\xd8" + app0 + sof0

def _webp(body: bytes, padding: int = 0) -> bytes:
    """
    Wrap a WebP bitstream chunk inside a RIFF container.

    Parameters
    ----------
    body : bytes
        Chunk identifier, size and payload of the bitstream.
    padding : int, optional
        Extra trailing bytes appended to reach the minimum header size.

    Returns
    -------
    bytes
        Complete RIFF container of a synthetic WebP.
    """
    return (
        b"RIFF"
        + struct.pack("<I", len(body) + 4)
        + b"WEBP"
        + body
        + b"\x00" * padding
    )

def _webp_lossy(width: int, height: int) -> bytes:
    """
    Build a lossy WebP header carrying the given dimensions.

    Parameters
    ----------
    width : int
        Width stored in the ``VP8`` bitstream.
    height : int
        Height stored in the ``VP8`` bitstream.

    Returns
    -------
    bytes
        Complete RIFF container of a synthetic lossy WebP.
    """
    body = (
        b"VP8 "
        + struct.pack("<I", 10)
        + b"\x00" * 3
        + b"\x9d\x01\x2a"
        + struct.pack("<HH", width, height)
    )
    return _webp(body)

def _webp_lossless(width: int, height: int) -> bytes:
    """
    Build a lossless WebP header carrying the given dimensions.

    Parameters
    ----------
    width : int
        Width stored in the ``VP8L`` bitstream.
    height : int
        Height stored in the ``VP8L`` bitstream.

    Returns
    -------
    bytes
        Complete RIFF container of a synthetic lossless WebP.
    """
    bits = (width - 1) | ((height - 1) << 14)
    body = b"VP8L" + struct.pack("<I", 5) + b"\x2f" + struct.pack("<I", bits)
    return _webp(body, padding=5)

def _webp_extended(width: int, height: int) -> bytes:
    """
    Build an extended WebP header carrying the given dimensions.

    Parameters
    ----------
    width : int
        Width stored in the ``VP8X`` chunk.
    height : int
        Height stored in the ``VP8X`` chunk.

    Returns
    -------
    bytes
        Complete RIFF container of a synthetic extended WebP.
    """
    body = (
        b"VP8X"
        + struct.pack("<I", 10)
        + b"\x00" * 4
        + (width - 1).to_bytes(3, "little")
        + (height - 1).to_bytes(3, "little")
    )
    return _webp(body)

def _upload(
    data: bytes,
    filename: str = "photo.png",
    content_type: str = "image/png",
) -> UploadedFile:
    """
    Build an uploaded file holding the given content.

    Parameters
    ----------
    data : bytes
        Content written into the upload buffer.
    filename : str, optional
        Client-supplied file name.
    content_type : str, optional
        MIME type declared by the client.

    Returns
    -------
    UploadedFile
        Upload ready to be handed to a rule.
    """
    upload = UploadedFile(filename, content_type)
    upload.write(data)
    return upload

class TestImageProbe(TestCase):

    def testEverySupportedFormatIsIdentified(self) -> None:
        """
        Read the format and dimensions of every supported raster header.

        Validates the PNG, JPEG, GIF, BMP and WebP probes at once.
        """
        cases = (
            ("png", _png(60, 40)),
            ("jpeg", _jpeg(300, 200)),
            ("gif", _gif(12, 34)),
            ("bmp", _bmp(100, 50)),
            ("webp", _webp_lossy(320, 240)),
        )
        expected = {
            "png": (60, 40),
            "jpeg": (300, 200),
            "gif": (12, 34),
            "bmp": (100, 50),
            "webp": (320, 240),
        }
        for name, blob in cases:
            probed = probe_image(blob)
            self.assertIsNotNone(probed)
            self.assertEqual(probed[0], name)
            self.assertEqual(probed[1:], expected[name])

    def testWebpVariantsAreIdentified(self) -> None:
        """
        Read the dimensions of the three WebP bitstream variants.

        Validates the lossy, lossless and extended layouts.
        """
        self.assertEqual(probe_image(_webp_lossy(320, 240)), ("webp", 320, 240))
        self.assertEqual(probe_image(_webp_lossless(320, 240)), ("webp", 320, 240))
        self.assertEqual(probe_image(_webp_extended(320, 240)), ("webp", 320, 240))

    def testUnknownContentReturnsNone(self) -> None:
        """
        Return None when the content matches no supported signature.

        Validates that plain text and truncated headers are rejected.
        """
        self.assertIsNone(probe_image(b"just plain text"))
        self.assertIsNone(probe_image(b""))
        self.assertIsNone(probe_image(b"\x89PNG\r\n\x1a\n"))

    def testUnknownWebpChunkReturnsNone(self) -> None:
        """
        Return None when the WebP chunk identifier is not supported.

        Validates that an unexpected bitstream is not misread.
        """
        self.assertIsNone(probe_image(_webp(b"XXXX" + b"\x00" * 14)))

class TestFile(TestCase):

    def testUploadedFilePasses(self) -> None:
        """
        Return True when the value is a non-empty uploaded file.

        Validates the ordinary success path.
        """
        self.assertTrue(File().enforce("doc", _upload(b"content"), _OWNER))

    def testEmptyUploadFails(self) -> None:
        """
        Return False when the upload carries no content.

        Validates that an interrupted transfer is rejected.
        """
        self.assertFalse(File().enforce("doc", _upload(b""), _OWNER))

    def testForeignValuesFail(self) -> None:
        """
        Return False when the value does not implement the upload protocol.

        Validates that plain data is never mistaken for a file.
        """
        rule = File()
        for value in ("text", b"bytes", None, 1, object()):
            self.assertFalse(rule.enforce("doc", value, _OWNER))

class TestMimeTypes(TestCase):

    def testExactTypeMatches(self) -> None:
        """
        Return True when the declared type is listed verbatim.

        Validates the exact matching path.
        """
        rule = MimeTypes("text/plain", "application/pdf")
        upload = _upload(b"a", "a.txt", "text/plain")
        self.assertTrue(rule.enforce("doc", upload, _OWNER))

    def testWildcardSubtypeMatches(self) -> None:
        """
        Return True when a wildcard covers the declared subtype.

        Validates that ``image/*`` accepts any image subtype.
        """
        rule = MimeTypes("image/*")
        self.assertTrue(rule.enforce("photo", _upload(b"a"), _OWNER))

    def testParametersAreIgnoredOnBothSides(self) -> None:
        """
        Compare MIME types after dropping any trailing parameter.

        Validates that charset parameters never break the comparison.
        """
        rule = MimeTypes("text/plain; charset=utf-8")
        upload = _upload(b"a", "a.txt", "text/plain; charset=iso-8859-1")
        self.assertTrue(rule.enforce("doc", upload, _OWNER))

    def testUnlistedTypeFails(self) -> None:
        """
        Return False when the declared type is not accepted.

        Validates that unrelated types and wildcards are rejected.
        """
        rule = MimeTypes("image/*")
        upload = _upload(b"a", "a.txt", "text/plain")
        self.assertFalse(rule.enforce("doc", upload, _OWNER))

    def testMissingContentTypeFails(self) -> None:
        """
        Return False when the upload declares no MIME type.

        Validates that an absent header is never accepted.
        """
        rule = MimeTypes("text/plain")
        upload = UploadedFile("a.txt", None)
        upload.write(b"a")
        self.assertFalse(rule.enforce("doc", upload, _OWNER))

    def testForeignValueFails(self) -> None:
        """
        Return False when the value is not an uploaded file.

        Validates that plain data is never mistaken for a file.
        """
        self.assertFalse(MimeTypes("text/plain").enforce("doc", "text", _OWNER))

    def testEmptyConfigurationRaises(self) -> None:
        """
        Raise ValueError when no MIME type is supplied.

        Validates that the rule refuses a configuration with no effect.
        """
        with self.assertRaises(ValueError):
            MimeTypes()

class TestSize(TestCase):

    def testFileSizeIsComparedInKilobytes(self) -> None:
        """
        Return True when the upload weighs exactly the required kilobytes.

        Validates the file size semantics.
        """
        rule = Size(1)
        self.assertTrue(rule.enforce("doc", _upload(b"x" * 1024), _OWNER))
        self.assertFalse(rule.enforce("doc", _upload(b"x" * 2048), _OWNER))

    def testStringAndNumberSemantics(self) -> None:
        """
        Compare strings by length and numbers by magnitude.

        Validates that the rule stays generic across value types.
        """
        rule = Size(3)
        self.assertTrue(rule.enforce("tag", "abc", _OWNER))
        self.assertTrue(rule.enforce("qty", 3, _OWNER))
        self.assertTrue(rule.enforce("items", [1, 2, 3], _OWNER))
        self.assertFalse(rule.enforce("tag", "ab", _OWNER))

    def testUnmeasurableValuePasses(self) -> None:
        """
        Return True when the value carries no comparable size.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(Size(3).enforce("tag", None, _OWNER))

    def testNegativeSizeRaises(self) -> None:
        """
        Raise ValueError when the required size is negative.

        Validates the configuration check performed at construction time.
        """
        with self.assertRaises(ValueError):
            Size(-1)

class TestImage(TestCase):

    def testEverySupportedFormatPasses(self) -> None:
        """
        Return True for uploads holding any supported raster format.

        Validates that detection relies on the header, not the extension.
        """
        rule = Image()
        for blob in (_png(2, 2), _jpeg(2, 2), _gif(2, 2), _bmp(2, 2)):
            self.assertTrue(rule.enforce("photo", _upload(blob), _OWNER))

    def testMislabelledUploadFails(self) -> None:
        """
        Return False when the content is not a raster image.

        Validates that a matching name and MIME type do not fool the rule.
        """
        upload = _upload(b"plain text", "photo.png", "image/png")
        self.assertFalse(Image().enforce("photo", upload, _OWNER))

    def testForeignValueFails(self) -> None:
        """
        Return False when the value is not an uploaded file.

        Validates that plain data is never mistaken for a file.
        """
        self.assertFalse(Image().enforce("photo", "text", _OWNER))

class TestDimensions(TestCase):

    def testExactDimensionsPass(self) -> None:
        """
        Return True when width and height match the required values.

        Validates the exact-size configuration.
        """
        rule = Dimensions(width=60, height=40)
        self.assertTrue(rule.enforce("photo", _upload(_png(60, 40)), _OWNER))
        self.assertFalse(rule.enforce("photo", _upload(_png(61, 40)), _OWNER))

    def testBoundsAreInclusive(self) -> None:
        """
        Return True when the dimensions sit on the configured bounds.

        Validates the minimum and maximum width and height checks.
        """
        rule = Dimensions(min_width=60, max_width=80, min_height=40, max_height=60)
        self.assertTrue(rule.enforce("photo", _upload(_png(60, 40)), _OWNER))
        self.assertTrue(rule.enforce("photo", _upload(_png(80, 60)), _OWNER))
        self.assertFalse(rule.enforce("photo", _upload(_png(59, 40)), _OWNER))
        self.assertFalse(rule.enforce("photo", _upload(_png(60, 61)), _OWNER))

    def testFractionRatioIsParsed(self) -> None:
        """
        Return True when the aspect ratio matches the given fraction.

        Validates the ``"width/height"`` textual form.
        """
        rule = Dimensions(ratio="3/2")
        self.assertTrue(rule.enforce("photo", _upload(_png(60, 40)), _OWNER))
        self.assertFalse(rule.enforce("photo", _upload(_png(60, 60)), _OWNER))

    def testNumericRatioIsAccepted(self) -> None:
        """
        Return True when the aspect ratio matches the given number.

        Validates that floats and numeric strings are supported.
        """
        upload = _upload(_png(60, 40))
        self.assertTrue(Dimensions(ratio=1.5).enforce("p", upload, _OWNER))
        self.assertTrue(Dimensions(ratio="1.5").enforce("p", upload, _OWNER))

    def testRatioBoundsAreApplied(self) -> None:
        """
        Return True when the aspect ratio sits inside the ratio bounds.

        Validates the minimum and maximum ratio checks.
        """
        upload = _upload(_png(60, 40))
        bounded = Dimensions(min_ratio=1.0, max_ratio=2.0)
        self.assertTrue(bounded.enforce("p", upload, _OWNER))
        self.assertFalse(Dimensions(min_ratio=2.0).enforce("p", upload, _OWNER))
        self.assertFalse(Dimensions(max_ratio=1.0).enforce("p", upload, _OWNER))

    def testNonImageValueFails(self) -> None:
        """
        Return False when the value is not a readable raster image.

        Validates that plain data and foreign values are rejected.
        """
        rule = Dimensions(width=60)
        self.assertFalse(rule.enforce("photo", _upload(b"plain"), _OWNER))
        self.assertFalse(rule.enforce("photo", "text", _OWNER))

    def testInvalidRatioRaises(self) -> None:
        """
        Raise ValueError when a ratio constraint cannot be parsed.

        Validates that free text, zero denominators and foreign types are
        rejected at construction time.
        """
        with self.assertRaises(ValueError):
            Dimensions(ratio="abc")
        with self.assertRaises(ValueError):
            Dimensions(ratio="3/0")
        with self.assertRaises(ValueError):
            Dimensions(min_ratio=object())

class TestEncoding(TestCase):

    def testEncodableStringPasses(self) -> None:
        """
        Return True when the string can be encoded with the codec.

        Validates the textual success path.
        """
        self.assertTrue(Encoding("ascii").enforce("tag", "plain", _OWNER))

    def testUnencodableStringFails(self) -> None:
        """
        Return False when the string cannot be encoded with the codec.

        Validates that accented text is rejected under ASCII.
        """
        self.assertFalse(Encoding("ascii").enforce("tag", "ñandú", _OWNER))

    def testDecodableUploadPasses(self) -> None:
        """
        Return True when the upload content decodes with the codec.

        Validates the file success path.
        """
        upload = _upload(b"plain", "a.txt", "text/plain")
        self.assertTrue(Encoding("ascii").enforce("doc", upload, _OWNER))

    def testUndecodableUploadFails(self) -> None:
        """
        Return False when the upload content does not decode.

        Validates that binary content is rejected under ASCII.
        """
        upload = _upload("ñandú".encode(), "a.txt", "text/plain")
        self.assertFalse(Encoding("ascii").enforce("doc", upload, _OWNER))

    def testDefaultCodecIsUtf8(self) -> None:
        """
        Accept UTF-8 content under the default configuration.

        Validates that the codec defaults to ``utf-8``.
        """
        upload = _upload("ñandú".encode(), "a.txt", "text/plain")
        self.assertTrue(Encoding().enforce("doc", upload, _OWNER))

    def testForeignValuePasses(self) -> None:
        """
        Return True when the value is neither a string nor a file.

        Validates that type reporting is delegated to the type layer.
        """
        self.assertTrue(Encoding("ascii").enforce("tag", 123, _OWNER))

    def testUnknownCodecRaises(self) -> None:
        """
        Raise ValueError when the configured codec does not exist.

        Validates the configuration check performed at construction time.
        """
        with self.assertRaises(ValueError):
            Encoding("not-a-codec")
