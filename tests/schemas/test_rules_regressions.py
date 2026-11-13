# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Exercise complete rule inputs, exact numeric values and upload failures."""

import asyncio
from decimal import Decimal
import struct
from threading import Event
from types import SimpleNamespace

from orionis.http.payload.uploaded_file import UploadedFile
from orionis.schemas.rules.after import After
from orionis.schemas.rules.after_or_equal import AfterOrEqual
from orionis.schemas.rules.before import Before
from orionis.schemas.rules.before_or_equal import BeforeOrEqual
from orionis.schemas.rules.between import Between
from orionis.schemas.rules.decimal_places import DecimalPlaces
from orionis.schemas.rules.dimensions import Dimensions
from orionis.schemas.rules.email import Email
from orionis.schemas.rules.encoding import Encoding
from orionis.schemas.rules.greater_than_or_equal_field import GreaterThanOrEqualField
from orionis.schemas.rules.integer import Integer
from orionis.schemas.rules.json_string import Json
from orionis.schemas.rules.image_probe import probe_image
from orionis.schemas.rules.less_than_or_equal_field import LessThanOrEqualField
from orionis.schemas.rules.mac_address import MacAddress
from orionis.schemas.rules.max_digits import MaxDigits
from orionis.schemas.rules.measure import read_content
from orionis.schemas.rules.size import Size
from orionis.schemas.rules.ulid import Ulid
from orionis.schemas.rules.uuid_string import Uuid
from orionis.test import TestCase


class TestRulesRegressions(TestCase):
    """Validate malformed boundaries through real asynchronous rule methods."""

    async def testAnchoredRulesRejectTrailingNewlines(self) -> None:
        """Require the entire textual value to match each rule's grammar."""
        for rule, valid in (
            (Integer(), "123"),
            (Email(), "user@example.com"),
            (MacAddress(), "00:1A:2B:3C:4D:5E"),
            (Uuid(), "550e8400-e29b-41d4-a716-446655440000"),
        ):
            with self.subTest(rule=type(rule).__name__):
                self.assertTrue(await rule.enforce("value", valid, object()))
                self.assertFalse(await rule.enforce("value", valid + "\n", object()))

    async def testMaxDigitsRejectsMalformedIntegerText(self) -> None:
        """Reject nondecimal characters and multiple signs before counting digits."""
        rule = MaxDigits(8)
        for value in ("abc", "12.34", "+-12", "-+12", " 123", "²"):
            with self.subTest(value=value):
                self.assertFalse(await rule.enforce("value", value, object()))

    async def testNumericRulesHandleIntegersBeyondTheStringConversionLimit(
        self,
    ) -> None:
        """Compare large integer magnitudes without changing Python's string limit."""
        value = 10**5000
        self.assertTrue(await MaxDigits(5001).enforce("value", value, object()))
        self.assertFalse(await MaxDigits(5000).enforce("value", value, object()))
        self.assertTrue(await DecimalPlaces(0).enforce("value", value, object()))

    async def testUlidRejectsUnicodeCaseExpansions(self) -> None:
        """Keep accepted identifiers inside the ASCII Crockford alphabet."""
        for suffix in ("ß", "\u017f"):
            with self.subTest(suffix=suffix):
                value = "0" + "A" * 24 + suffix
                self.assertEqual(len(value), 26)
                self.assertFalse(await Ulid().enforce("value", value, object()))

    async def testMagnitudeRulesPreserveDecimalPrecision(self) -> None:
        """Compare decimal values without first rounding them to binary floats."""
        owner = SimpleNamespace(limit=Decimal(1))
        above = Decimal("1.000000000000000000001")
        below = Decimal("0.999999999999999999999")
        for rule, value in (
            (Size(1), above),
            (Between(0, 1), above),
            (LessThanOrEqualField("limit"), above),
            (GreaterThanOrEqualField("limit"), below),
        ):
            with self.subTest(rule=type(rule).__name__):
                self.assertFalse(await rule.enforce("value", value, owner))
                self.assertTrue(await rule.enforce("value", Decimal(1), owner))

    async def testEncodingRejectsUnreadableUploads(self) -> None:
        """Fail validation when an upload cannot provide readable content."""
        upload = UploadedFile("closed.txt", "text/plain")
        upload.write(b"content")
        upload.close()
        self.assertFalse(await Encoding().enforce("value", upload, object()))

    async def testCancelledReadWaitsBeforeReturningBorrowedUpload(self) -> None:
        """Keep an upload borrowed until its running synchronous read finishes."""
        loop = asyncio.get_running_loop()
        started = asyncio.Event()
        released = Event()
        finished = Event()

        def read() -> bytes:
            """Hold the borrowed upload until the test releases the reader."""
            loop.call_soon_threadsafe(started.set)
            try:
                if not released.wait(5):
                    message = "The test did not release its reader."
                    raise TimeoutError(message)
                return b"content"
            finally:
                finished.set()

        upload = SimpleNamespace(read=read, size=7, filename="borrowed.txt")
        pending = asyncio.create_task(read_content(upload))
        try:
            await asyncio.wait_for(started.wait(), timeout=5)
            pending.cancel()
            await asyncio.sleep(0)
            self.assertFalse(finished.is_set())
            self.assertFalse(pending.done())
        finally:
            released.set()
            await asyncio.gather(pending, return_exceptions=True)
        self.assertTrue(finished.is_set())
        self.assertTrue(pending.cancelled())

    def testImageProbesRejectMalformedDimensionHeaders(self) -> None:
        """Reject invalid required chunks, marker lengths and zero dimensions."""
        png = b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
        webp = b"RIFF" + struct.pack("<I", 22) + b"WEBP"
        for name, data in (
            ("png chunk", png[:12] + b"JUNK" + struct.pack(">II", 1, 1)),
            ("png zero", png + struct.pack(">II", 0, 1)),
            ("jpeg segment", b"\xff\xd8\xff\xc0\x00\x01\x08\x00\x10\x00\x10"),
            (
                "webp lossless signature",
                webp + b"VP8L" + struct.pack("<I", 5) + b"\x00" * 10,
            ),
            (
                "webp lossy signature",
                webp
                + b"VP8 "
                + struct.pack("<I", 10)
                + b"\x00" * 6
                + struct.pack("<HH", 1, 1),
            ),
        ):
            with self.subTest(format=name):
                self.assertIsNone(probe_image(data))

    def testImageProbesUseEachFormatsDimensionLayout(self) -> None:
        """Read compact BMP and lossless WebP dimension headers accurately."""
        bitmap = b"BM" + b"\x00" * 12 + struct.pack("<IHHHH", 12, 2, 3, 1, 24)
        webp = (
            b"RIFF"
            + struct.pack("<I", 18)
            + b"WEBPVP8L"
            + struct.pack("<I", 5)
            + b"\x2f"
            + struct.pack("<I", 1 | (2 << 14))
            + b"\x00"
        )
        for data, expected in (
            (bitmap, ("bmp", 2, 3)),
            (webp, ("webp", 2, 3)),
        ):
            with self.subTest(format=expected[0]):
                self.assertEqual(probe_image(data), expected)

    async def testTemporalRulesRejectUnparseableStringValues(self) -> None:
        """Reject malformed text that the schema's string type otherwise accepts."""
        for rule in (
            After("2024-01-01"),
            AfterOrEqual("2024-01-01"),
            Before("2024-01-01"),
            BeforeOrEqual("2024-01-01"),
        ):
            with self.subTest(rule=type(rule).__name__):
                self.assertFalse(await rule.enforce("when", "not-a-date", object()))
                self.assertTrue(await rule.enforce("when", None, object()))

    def testDimensionsRejectsNonfiniteRatios(self) -> None:
        """Reject ratio bounds whose NaN or infinity invalidates comparisons."""
        for name in ("ratio", "min_ratio", "max_ratio"):
            for value in (float("nan"), float("inf"), "NaN"):
                with (
                    self.subTest(bound=name, value=value),
                    self.assertRaises(ValueError),
                ):
                    Dimensions(**{name: value})

    async def testJsonRejectsUnencodableUnicode(self) -> None:
        """Reject invalid Unicode text without leaking an encoder exception."""
        self.assertFalse(await Json().enforce("value", '"\ud800"', object()))
