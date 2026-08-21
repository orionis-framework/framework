from __future__ import annotations
import datetime
import decimal
import enum
import tempfile
import uuid
from pathlib import Path
from orionis.cache.serializer import Serializer
from orionis.support.types.sentinel import MISSING
from orionis.test import TestCase

class _Color(enum.Enum):
    RED = 1
    GREEN = 2

class TestSerializer(TestCase):

    def testDumpsAndLoadsPrimitives(self) -> None:
        """
        Round-trip primitive scalar values through the serializer.

        Validates that str, int, float, bool, and None survive a full
        dumps/loads cycle with both value and type preserved.
        """
        cases = ["hello", "", 0, -1, 42, 3.14, -0.5, True, False, None]
        for value in cases:
            with self.subTest(value=value):
                result = Serializer.loads(Serializer.dumps(value))
                self.assertEqual(result, value)
                self.assertIs(type(result), type(value))

    def testDumpsAndLoadsPath(self) -> None:
        """
        Round-trip a Path object through the serializer.

        Validates that a Path value is encoded and decoded back to the
        same logical path.
        """
        original = Path("some/nested/path")
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)
        self.assertIsInstance(result, Path)

    def testDumpsAndLoadsBytes(self) -> None:
        """
        Round-trip a bytes object through the serializer.

        Validates that arbitrary binary data survives base64
        encoding/decoding without loss.
        """
        original = b"\x00\xff\xab\xcd\x00"
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)
        self.assertIsInstance(result, bytes)

    def testDumpsAndLoadsBytesEmpty(self) -> None:
        """
        Round-trip an empty bytes object through the serializer.

        Validates that a zero-length byte string is preserved correctly.
        """
        result = Serializer.loads(Serializer.dumps(b""))
        self.assertEqual(result, b"")

    def testDumpsAndLoadsDatetime(self) -> None:
        """
        Round-trip a datetime.datetime through the serializer.

        Validates that the full datetime value including time components
        is preserved via ISO format encoding.
        """
        original = datetime.datetime(
            2024, 6, 15, 12, 30, 45, tzinfo=datetime.UTC,
        )
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)
        self.assertIsInstance(result, datetime.datetime)

    def testDumpsAndLoadsDate(self) -> None:
        """
        Round-trip a datetime.date through the serializer.

        Validates that a calendar date is preserved via ISO format.
        """
        original = datetime.date(2024, 6, 15)
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)
        self.assertIsInstance(result, datetime.date)
        self.assertNotIsInstance(result, datetime.datetime)

    def testDumpsAndLoadsTime(self) -> None:
        """
        Round-trip a datetime.time through the serializer.

        Validates that hours, minutes, and seconds are preserved via
        ISO format encoding.
        """
        original = datetime.time(12, 30, 45)
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)
        self.assertIsInstance(result, datetime.time)

    def testDumpsAndLoadsTimedelta(self) -> None:
        """
        Round-trip a datetime.timedelta through the serializer.

        Validates that days, seconds, and microseconds fields survive
        the encode/decode cycle intact.
        """
        original = datetime.timedelta(days=3, seconds=7200, microseconds=500)
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)
        self.assertIsInstance(result, datetime.timedelta)

    def testDumpsAndLoadsDecimal(self) -> None:
        """
        Round-trip a decimal.Decimal through the serializer.

        Validates that high-precision decimal values are preserved as
        exact strings without floating-point drift.
        """
        original = decimal.Decimal("3.141592653589793238")
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)
        self.assertIsInstance(result, decimal.Decimal)

    def testDumpsAndLoadsUuid(self) -> None:
        """
        Round-trip a uuid.UUID through the serializer.

        Validates that the UUID value is preserved without modification.
        """
        original = uuid.UUID("12345678-1234-5678-1234-567812345678")
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)
        self.assertIsInstance(result, uuid.UUID)

    def testDumpsAndLoadsComplex(self) -> None:
        """
        Round-trip a complex number through the serializer.

        Validates that both real and imaginary components are preserved.
        """
        original = complex(3.0, -4.5)
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)
        self.assertIsInstance(result, complex)

    def testDumpsAndLoadsTuple(self) -> None:
        """
        Round-trip a heterogeneous tuple through the serializer.

        Validates that the decoded result is a tuple and its elements
        are preserved in order.
        """
        original = (1, "a", 3.0, None)
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)
        self.assertIsInstance(result, tuple)

    def testDumpsAndLoadsTupleEmpty(self) -> None:
        """
        Round-trip an empty tuple through the serializer.

        Validates that an empty tuple is decoded back as an empty tuple.
        """
        result = Serializer.loads(Serializer.dumps(()))
        self.assertEqual(result, ())
        self.assertIsInstance(result, tuple)

    def testDumpsAndLoadsSet(self) -> None:
        """
        Round-trip a set of integers through the serializer.

        Validates that the decoded result is a set with identical elements.
        """
        original = {1, 2, 3, 4}
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)
        self.assertIsInstance(result, set)

    def testDumpsAndLoadsFrozenset(self) -> None:
        """
        Round-trip a frozenset through the serializer.

        Validates that the decoded result is a frozenset with identical
        elements.
        """
        original = frozenset([10, 20, 30])
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)
        self.assertIsInstance(result, frozenset)

    def testDumpsAndLoadsMissingSentinel(self) -> None:
        """
        Round-trip the MISSING sentinel through the serializer.

        Validates that the sentinel is decoded back as the exact same
        singleton instance.
        """
        result = Serializer.loads(Serializer.dumps(MISSING))
        self.assertIs(result, MISSING)

    def testDumpsAndLoadsNestedDict(self) -> None:
        """
        Round-trip a deeply nested dictionary through the serializer.

        Validates that nested mappings and mixed-type values are preserved
        at all levels.
        """
        original = {"a": {"b": {"c": 42}}, "x": [1, 2, 3], "flag": True}
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)

    def testDumpsAndLoadsNestedList(self) -> None:
        """
        Round-trip a nested list through the serializer.

        Validates that deeply nested list structures are preserved.
        """
        original = [[1, 2], [3, [4, 5]], []]
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)

    def testDumpsAndLoadsEmptyContainers(self) -> None:
        """
        Round-trip empty dict and list through the serializer.

        Validates that empty containers are decoded back with the correct
        type and zero elements.
        """
        result_dict = Serializer.loads(Serializer.dumps({}))
        self.assertEqual(result_dict, {})
        self.assertIsInstance(result_dict, dict)

        result_list = Serializer.loads(Serializer.dumps([]))
        self.assertEqual(result_list, [])
        self.assertIsInstance(result_list, list)

    def testDumpsAndLoadsLargeInt(self) -> None:
        """
        Round-trip an arbitrarily large integer through the serializer.

        Validates that Python's arbitrary-precision integers survive the
        encode/decode cycle.
        """
        original = 10**50
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)

    def testDumpsAndLoadsEnum(self) -> None:
        """
        Round-trip an enum member through the serializer.

        Validates that the enum class path and value are preserved and
        the decoded result is the correct enum member.
        """
        original = _Color.GREEN
        result = Serializer.loads(Serializer.dumps(original))
        self.assertEqual(result, original)
        self.assertIsInstance(result, _Color)

    def testDumpsAndLoadsTypeReference(self) -> None:
        """
        Round-trip a type (class) object through the serializer.

        Validates that a class reference is encoded as a dotted path and
        decoded back to the same class object.
        """
        result = Serializer.loads(Serializer.dumps(Path))
        self.assertIs(result, Path)

    def testDumpsWithIndentProducesFormattedJson(self) -> None:
        """
        Produce indented JSON output when indent is specified.

        Validates that passing a non-None indent argument causes the
        output string to contain newline characters.
        """
        output = Serializer.dumps({"key": "value", "num": 1}, indent=2)
        self.assertIn("\n", output)

    def testDumpsWithoutIndentProducesCompactJson(self) -> None:
        """
        Produce compact JSON output when indent is omitted.

        Validates that the default (no indent) encoding does not insert
        unnecessary whitespace.
        """
        output = Serializer.dumps({"key": "value"})
        self.assertNotIn("\n", output)

    def testDumpsUnsupportedTypeRaisesTypeError(self) -> None:
        """
        Raise TypeError when serializing an unsupported object.

        Validates that attempting to encode a plain object() raises
        TypeError rather than silently producing invalid output.
        """
        with self.assertRaises(TypeError):
            Serializer.dumps(object())

    def testLoadsUnknownTypeKeyRaisesValueError(self) -> None:
        """
        Raise ValueError when decoding a payload with an unknown type key.

        Validates that a serialized mapping containing an unregistered
        type discriminator raises ValueError.
        """
        raw = '{"__type__":"unsupported_xyz","__value__":null}'
        with self.assertRaises(ValueError):
            Serializer.loads(raw)

    def testDumpToFileAndLoadFromFileRoundtrip(self) -> None:
        """
        Serialize data to disk and reload it without loss.

        Validates that the full dumpToFile/loadFromFile cycle preserves
        the original data structure.
        """
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "payload.bin"
            data = {"x": 1, "y": [1, 2, 3], "z": True, "w": None}
            Serializer.dumpToFile(data, file_path)
            result = Serializer.loadFromFile(file_path)
            self.assertEqual(result, data)

    def testDumpToFileCreatesFile(self) -> None:
        """
        Create the target file after a successful dumpToFile call.

        Validates that dumpToFile produces a non-empty file on disk.
        """
        with tempfile.TemporaryDirectory() as tmp:
            file_path = Path(tmp) / "out.bin"
            Serializer.dumpToFile({"a": 1}, file_path)
            self.assertTrue(file_path.exists())
            self.assertGreater(file_path.stat().st_size, 0)

    def testDumpToFileLeavesNoStagingFileBehind(self) -> None:
        """
        Remove the staging file once the payload is published.

        Validates that the unique ``.tmp`` sibling used for the atomic
        write is renamed away instead of accumulating on disk.
        """
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            Serializer.dumpToFile({"a": 1}, directory / "out.bin")
            self.assertEqual(list(directory.glob("*.tmp")), [])

    def testFailedDumpToFileRemovesItsStagingFile(self) -> None:
        """
        Clean up the staging file when the publish step fails.

        Validates the failure path by targeting an existing directory,
        which makes the rename raise a portable OSError.
        """
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            occupied = directory / "busy"
            occupied.mkdir()

            with self.assertRaises(OSError):
                Serializer.dumpToFile({"a": 1}, occupied)

            self.assertEqual(list(directory.glob("*.tmp")), [])

    def testLoadFromFileMissingReturnsNone(self) -> None:
        """
        Return None when the target file does not exist.

        Validates that loadFromFile handles a missing path gracefully
        without raising an exception.
        """
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "nonexistent.bin"
            result = Serializer.loadFromFile(missing)
            self.assertIsNone(result)

    def testLoadFromFileEmptyReturnsNone(self) -> None:
        """
        Return None when the target file is empty.

        Validates that loadFromFile returns None rather than raising
        when reading a zero-byte file.
        """
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.bin"
            empty.write_bytes(b"")
            result = Serializer.loadFromFile(empty)
            self.assertIsNone(result)

    def testLoadsRawBytesInput(self) -> None:
        """
        Accept raw bytes as input to loads.

        Validates that loads handles a bytes argument the same way it
        handles a string, returning the correct deserialized value.
        """
        raw = Serializer.dumps({"k": 99})
        result = Serializer.loads(raw.encode())
        self.assertEqual(result, {"k": 99})
