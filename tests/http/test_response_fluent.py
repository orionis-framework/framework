# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions and deliberate invalid argument probes.
"""Verify fluent HTTP options on constructed responses."""

from types import MappingProxyType
from orionis.background.task import BackgroundTask
from orionis.http.enums.status import HTTPStatus
from orionis.http.responses import HTMLResponse, RedirectResponse, Response
from orionis.test import TestCase


class TestResponseFluentOptions(TestCase):
    """Exercise option validation and preservation of existing response state."""

    def testFluentOptionsReturnTheSameHtmlResponse(self) -> None:
        """Configure a rendered response without replacing its body or identity.

        Returns
        -------
        None
            No return value.
        """
        response = HTMLResponse("<h1>Unauthorized</h1>")
        task = BackgroundTask(lambda: None)

        self.assertIs(response.withStatusCode(HTTPStatus.UNAUTHORIZED), response)
        self.assertIs(response.withHeaders({"Cache-Control": "no-store"}), response)
        self.assertIs(response.withBackground(task), response)
        self.assertEqual(response.getStatusCode(), 401)
        self.assertEqual(response.getHeader("cache-control"), ["no-store"])
        self.assertEqual(
            response.getHeader("content-type"),
            ["text/html; charset=utf-8"],
        )
        self.assertEqual(response.getBody(), b"<h1>Unauthorized</h1>")
        self.assertIs(response.background, task)

    def testStatusCodeAcceptsIntegersThroughoutTheSupportedRange(self) -> None:
        """Retain the constructor's status bounds and integer support.

        Returns
        -------
        None
            No return value.
        """
        response = Response()
        for status_code in (100, 201, 599):
            with self.subTest(status_code=status_code):
                self.assertIs(response.withStatusCode(status_code), response)
                self.assertEqual(response.getStatusCode(), status_code)

    def testInvalidStatusCodesLeaveTheExistingStatusUnchanged(self) -> None:
        """Reject invalid status values before mutating the response.

        Returns
        -------
        None
            No return value.
        """
        response = Response(status_code=401)
        for status_code, error in (
            ("402", TypeError),
            (402.0, TypeError),
            (None, TypeError),
            (99, ValueError),
            (600, ValueError),
        ):
            with self.subTest(status_code=status_code):
                with self.assertRaises(error):
                    response.withStatusCode(status_code)
                self.assertEqual(response.getStatusCode(), 401)

    def testRedirectStatusChangesPreserveTheRedirectRange(self) -> None:
        """Accept redirect statuses while keeping the original destination.

        Returns
        -------
        None
            No return value.
        """
        response = RedirectResponse("/login")
        for status_code in (300, HTTPStatus.SEE_OTHER, 399):
            with self.subTest(status_code=status_code):
                self.assertIs(response.withStatusCode(status_code), response)
                self.assertEqual(response.getStatusCode(), status_code)
                self.assertEqual(response.getHeader("location"), ["/login"])

    def testInvalidRedirectStatusesLeaveTheExistingStatusUnchanged(self) -> None:
        """Reject non-redirect codes and invalid types before mutation.

        Returns
        -------
        None
            No return value.
        """
        response = RedirectResponse("/login")
        for status_code, error in (
            ("307", TypeError),
            (307.0, TypeError),
            (None, TypeError),
            (200, ValueError),
            (400, ValueError),
        ):
            with self.subTest(status_code=status_code):
                with self.assertRaises(error):
                    response.withStatusCode(status_code)
                self.assertEqual(response.getStatusCode(), 302)

    def testHeadersMergeMappingsAndRefreshPreviouslyExportedHeaders(self) -> None:
        """Replace named headers while preserving cookies and unrelated values.

        Returns
        -------
        None
            No return value.
        """
        response = HTMLResponse("ready", headers={"X-Existing": "old"})
        response.withCookie("first", "one").withCookie("second", "two")
        response.addHeader("X-Existing", "also-old")
        before = response.getRawHeaders()
        cookies = [pair for pair in before if pair[0] == b"set-cookie"]
        headers = MappingProxyType({"x-EXISTING": "new", "X-Added": "yes"})

        self.assertIs(response.withHeaders(headers), response)
        after = response.getRawHeaders()
        self.assertIn((b"x-existing", b"new"), after)
        self.assertIn((b"x-added", b"yes"), after)
        self.assertNotIn((b"x-existing", b"old"), after)
        self.assertNotIn((b"x-existing", b"also-old"), after)
        self.assertIn((b"content-type", b"text/html; charset=utf-8"), after)
        self.assertEqual([pair for pair in after if pair[0] == b"set-cookie"], cookies)
        self.assertEqual(headers["x-EXISTING"], "new")
        self.assertIs(response.withHeaders({}), response)
        self.assertEqual(response.getRawHeaders(), after)

    def testHeadersRejectNonMappingsBeforeChangingTheResponse(self) -> None:
        """Reject unsupported header containers, including empty ones.

        Returns
        -------
        None
            No return value.
        """
        response = Response(headers={"X-Existing": "original"})
        for headers in (None, [], [("X-Existing", "replacement")], "header"):
            with self.subTest(headers=headers):
                with self.assertRaises(TypeError):
                    response.withHeaders(headers)
                self.assertEqual(response.getHeader("X-Existing"), ["original"])

    def testBackgroundCanBeReplacedAndClearedWithoutExecution(self) -> None:
        """Replace or clear queued work while leaving execution to delivery.

        Returns
        -------
        None
            No return value.
        """
        calls = []
        first = BackgroundTask(calls.append, "first")
        second = BackgroundTask(calls.append, "second")
        response = Response(background=first)

        self.assertIs(response.withBackground(second), response)
        self.assertIs(response.background, second)
        self.assertIs(response.withBackground(None), response)
        self.assertIsNone(response.background)
        self.assertEqual(calls, [])

    def testInvalidBackgroundLeavesTheExistingTaskUnchanged(self) -> None:
        """Reject arbitrary callables and values as background tasks.

        Returns
        -------
        None
            No return value.
        """
        task = BackgroundTask(lambda: None)
        response = Response(background=task)
        for background in (lambda: None, "task", object()):
            with self.subTest(background=background):
                with self.assertRaises(TypeError):
                    response.withBackground(background)
                self.assertIs(response.background, task)
