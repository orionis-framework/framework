from __future__ import annotations
from orionis.cache.serializers.json import MsgspecSerializer
from orionis.test import TestCase

class TestMsgspecSerializer(TestCase):

    def setUp(self) -> None:
        """
        Create a fresh MsgspecSerializer instance before each test.

        Ensures every test receives an isolated serializer with no
        shared state between runs.
        """
        self._ser = MsgspecSerializer()

    def testDumpsReturnsBytesForString(self) -> None:
        """
        Return bytes from dumps when encoding a plain string.

        Validates that dumps always produces a bytes object, never a str,
        so it can be stored directly by raw-byte backends.
        """
        result = self._ser.dumps("hello")
        self.assertIsInstance(result, bytes)

    def testDumpsReturnsBytesForInteger(self) -> None:
        """
        Return bytes from dumps when encoding an integer.

        Validates that numeric types pass through the encoder without
        error and produce a non-empty bytes payload.
        """
        result = self._ser.dumps(42)
        self.assertIsInstance(result, bytes)
        self.assertGreater(len(result), 0)

    def testDumpsReturnsBytesForDict(self) -> None:
        """
        Return bytes from dumps when encoding a mapping.

        Validates that dict values are serialised to a bytes payload
        that can be decoded back by loads.
        """
        result = self._ser.dumps({"key": "value"})
        self.assertIsInstance(result, bytes)

    def testLoadsDecodesFromBytes(self) -> None:
        """
        Decode a bytes payload produced by dumps back to a Python value.

        Validates that loads(dumps(x)) == x for a representative string.
        """
        result = self._ser.loads(self._ser.dumps("world"))
        self.assertEqual(result, "world")

    def testLoadsDecodesFromString(self) -> None:
        """
        Accept a str argument in loads and return the decoded value.

        Validates the internal str-to-bytes coercion path so backends
        that return text can be handled transparently.
        """
        raw_bytes = self._ser.dumps(99)
        result = self._ser.loads(raw_bytes.decode())
        self.assertEqual(result, 99)

    def testLoadsNoneReturnsNone(self) -> None:
        """
        Return None when loads receives None.

        Validates the None guard that converts a backend "key not found"
        sentinel (None) into a Python None without decoding errors.
        """
        self.assertIsNone(self._ser.loads(None))

    def testLoadsReturnsNativeIntegerUnchanged(self) -> None:
        """
        Return an integer payload untouched instead of decoding it.

        Validates the passthrough that keeps the counters written by the
        aiocache memory backend readable: increment() stores a raw int,
        skipping dumps().
        """
        self.assertEqual(self._ser.loads(7), 7)

    def testLoadsReturnsNativeFloatUnchanged(self) -> None:
        """
        Return a float payload untouched instead of decoding it.

        Validates that the passthrough is not restricted to integers.
        """
        self.assertAlmostEqual(self._ser.loads(1.5), 1.5)

    def testLoadsDecodesFromByteArray(self) -> None:
        """
        Decode a bytearray payload like a plain bytes payload.

        Validates that mutable byte buffers are still routed to the JSON
        decoder rather than being returned unchanged.
        """
        result = self._ser.loads(bytearray(self._ser.dumps("buffered")))
        self.assertEqual(result, "buffered")

    def testRoundtripInteger(self) -> None:
        """
        Preserve an integer through a full dumps/loads cycle.

        Validates that numeric identity and type are retained across
        the serialization boundary.
        """
        result = self._ser.loads(self._ser.dumps(1234))
        self.assertEqual(result, 1234)

    def testRoundtripNegativeInteger(self) -> None:
        """
        Preserve a negative integer through a full dumps/loads cycle.

        Validates sign handling in the JSON encoder/decoder.
        """
        result = self._ser.loads(self._ser.dumps(-7))
        self.assertEqual(result, -7)

    def testRoundtripFloat(self) -> None:
        """
        Preserve a float through a full dumps/loads cycle.

        Validates that fractional values survive serialization without
        precision loss detectable by equality comparison.
        """
        result = self._ser.loads(self._ser.dumps(3.14))
        self.assertAlmostEqual(result, 3.14)

    def testRoundtripBoolTrue(self) -> None:
        """
        Preserve True through a full dumps/loads cycle.

        Validates that the boolean sentinel True is not confused with
        the integer 1 after decoding.
        """
        result = self._ser.loads(self._ser.dumps(True))
        self.assertIs(result, True)

    def testRoundtripBoolFalse(self) -> None:
        """
        Preserve False through a full dumps/loads cycle.

        Validates that the boolean sentinel False is not confused with
        the integer 0 after decoding.
        """
        result = self._ser.loads(self._ser.dumps(False))
        self.assertIs(result, False)

    def testRoundtripNone(self) -> None:
        """
        Preserve None through a full dumps/loads cycle.

        Validates that None survives serialization and is not converted
        to another falsy value during decoding.
        """
        result = self._ser.loads(self._ser.dumps(None))
        self.assertIsNone(result)

    def testRoundtripDict(self) -> None:
        """
        Preserve a flat dict through a full dumps/loads cycle.

        Validates that mapping structure and all scalar values survive
        serialization unchanged.
        """
        data = {"key": "value", "n": 7, "flag": True}
        result = self._ser.loads(self._ser.dumps(data))
        self.assertEqual(result, data)

    def testRoundtripList(self) -> None:
        """
        Preserve a list through a full dumps/loads cycle.

        Validates that ordered sequences are decoded back as lists with
        identical elements and preserved ordering.
        """
        data = [1, "two", 3.0, None]
        result = self._ser.loads(self._ser.dumps(data))
        self.assertEqual(result, data)

    def testRoundtripEmptyDict(self) -> None:
        """
        Preserve an empty dict through a full dumps/loads cycle.

        Validates that zero-element mappings are handled without error
        and decoded to the correct type.
        """
        result = self._ser.loads(self._ser.dumps({}))
        self.assertEqual(result, {})
        self.assertIsInstance(result, dict)

    def testRoundtripEmptyList(self) -> None:
        """
        Preserve an empty list through a full dumps/loads cycle.

        Validates that zero-element sequences round-trip as lists.
        """
        result = self._ser.loads(self._ser.dumps([]))
        self.assertEqual(result, [])
        self.assertIsInstance(result, list)

    def testRoundtripNestedStructure(self) -> None:
        """
        Preserve a nested dict/list structure through a full cycle.

        Validates that multi-level nesting is decoded back with the
        correct shape and values at every level.
        """
        data = {"outer": {"inner": [1, 2, {"deep": True}]}}
        result = self._ser.loads(self._ser.dumps(data))
        self.assertEqual(result, data)

    def testDefaultEncodingIsNone(self) -> None:
        """
        Confirm DEFAULT_ENCODING is None to suppress automatic decoding.

        Validates that the serializer class opts out of UTF-8 auto-decode
        so backends receive raw bytes rather than strings.
        """
        self.assertIsNone(MsgspecSerializer.DEFAULT_ENCODING)

    def testDumpsProducesNonEmptyPayload(self) -> None:
        """
        Confirm dumps produces a non-empty payload for any non-null value.

        Validates that the encoder always emits at least one byte, ruling
        out silent empty-output bugs.
        """
        for value in ["x", 0, False, [], {}]:
            with self.subTest(value=value):
                self.assertGreater(len(self._ser.dumps(value)), 0)
