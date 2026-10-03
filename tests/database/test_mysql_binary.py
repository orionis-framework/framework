from types import SimpleNamespace
from orionis.database.dialect import (
    _MySQLParameterEscaper,
    _configure_mysql_binary_parameters,
)
from orionis.test import TestCase

class _Driver:

    def escape(self, value: object) -> str:
        """Simulate the driver's removed binary converter.

        Parameters
        ----------
        value : object
            Bound parameter value.

        Returns
        -------
        str
            Original conversion for a nonbinary parameter.

        Raises
        ------
        TypeError
            If binary conversion reaches the incompatible upstream path.
        """
        if isinstance(value, bytes):
            message = "Upstream binary converter is not callable."
            raise TypeError(message)
        return repr(value)

class TestMySQLBinaryParameters(TestCase):
    def testEveryBinaryByteUsesAnExactHexLiteral(self) -> None:
        """Preserve every byte in an exact binary hex literal.

        Returns
        -------
        None
            Verify the literal round-trips all byte values unchanged.
        """
        contents = bytes(range(256))
        escaped = _MySQLParameterEscaper(_Driver().escape)(contents)
        self.assertTrue(escaped.startswith("_binary X'"))
        self.assertTrue(escaped.endswith("'"))
        self.assertEqual(bytes.fromhex(escaped[len("_binary X'"):-1]), contents)

    def testMutableBinaryAndEmptyValuesRemainBinary(self) -> None:
        """Handle mutable and empty binary payloads exactly.

        Returns
        -------
        None
            Verify bytearray, memoryview and empty values remain binary.
        """
        escaped = _MySQLParameterEscaper(_Driver().escape)
        for value in (b"", bytearray(b"a'\\\x00"), memoryview(b"\xff\x81'")):
            literal = escaped(value)
            self.assertEqual(bytes.fromhex(literal[len("_binary X'"):-1]), bytes(value))

    def testNonbinaryParametersRetainTheirDriverConversion(self) -> None:
        """Delegate scalar values to the driver's escape method.

        Returns
        -------
        None
            Verify nonbinary values retain the driver's conversion.
        """
        driver = _Driver()
        escaped = _MySQLParameterEscaper(driver.escape)
        for value in (None, 1, 1.5, "plain", "quote'and\\backslash"):
            self.assertEqual(escaped(value), driver.escape(value))

    def testConnectionHookIsLocalAndIdempotent(self) -> None:
        """Keep the binary escape hook local and idempotent.

        Returns
        -------
        None
            Verify repeated configuration affects only the target connection.
        """
        connection, other = _Driver(), _Driver()
        adapter = SimpleNamespace(driver_connection=connection)
        _configure_mysql_binary_parameters(adapter)
        first = connection.escape
        _configure_mysql_binary_parameters(adapter)
        self.assertIs(connection.escape, first)
        self.assertEqual(connection.escape(b"\x00"), "_binary X'00'")
        with self.assertRaises(TypeError):
            other.escape(b"\x00")
        _configure_mysql_binary_parameters(SimpleNamespace())
