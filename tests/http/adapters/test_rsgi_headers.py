from typing import Self
from orionis.http.adapters.request.rsgi import RSGITransportAdapter
from orionis.test import TestCase
from tests.http.test_kernel import (
    _StubRsgiHeaders,
    _StubRsgiProtocol,
    _StubRsgiScope,
    boot_kernel,
)

class TestRsgiHeaders(TestCase):
    """Preserve header semantics through the RSGI normalization path."""

    def testMixedCaseHeadersKeepDuplicatesEmptyValuesAndOrder(self: Self) -> None:
        """Retain every header value while exposing lowercase stored names.

        Returns
        -------
        None
            Case-insensitive lookup and cached header ownership remain intact.
        """
        scope = _StubRsgiScope("/api")
        source = {
            "X-Name": ["", "second"],
            "x-NAME": ["third"],
            "Cookie": ["a=1", "b=2"],
            "Host": ["orionis.test"],
            "X-Empty-Group": [],
        }
        scope.headers = _StubRsgiHeaders(source)
        adapter = RSGITransportAdapter(scope)
        headers = adapter.headers()
        self.assertEqual(
            headers.items(),
            [
                ("x-name", ""),
                ("x-name", "second"),
                ("x-name", "third"),
                ("cookie", "a=1"),
                ("cookie", "b=2"),
                ("host", "orionis.test"),
            ],
        )
        self.assertEqual(headers.get("X-NAME"), "third")
        self.assertEqual(headers.getAll("COOKIE"), ["a=1", "b=2"])
        self.assertEqual(headers.count("x-name"), 3)
        self.assertFalse(headers.hasInvalidFormat())
        self.assertIs(headers, adapter.headers())
        source["X-Name"].append("later")
        source["Cookie"].clear()
        self.assertEqual(headers.getAll("x-name"), ["", "second", "third"])
        self.assertEqual(headers.getAll("cookie"), ["a=1", "b=2"])
        self.assertNotIn("x-empty-group", headers)

    async def testKernelRejectsInvalidHeadersAfterNormalization(self: Self) -> None:
        """Reject injection, duplicate Host and ambiguous body framing in RSGI.

        Returns
        -------
        None
            Invalid requests still return 400 through the full kernel entry point.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        cases = (
            {"X-Invalid\n": ["value"]},
            {"X-Value": ["value\r\ninjected"]},
            {"Host": ["orionis.test"], "host": ["other.test"]},
            {"Content-Length": ["1", "1"]},
            {"Content-Length": ["1"], "content-length": ["2"]},
            {"Content-Length": ["1"], "Transfer-Encoding": ["chunked"]},
        )
        for values in cases:
            with self.subTest(values=values):
                scope = _StubRsgiScope("/api")
                scope.headers = _StubRsgiHeaders(values)
                response = await kernel.handleRSGI(scope, _StubRsgiProtocol())
                self.assertEqual(response.getStatusCode(), 400)
