# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions and deferred validation checks.
"""Verify HTTP options on deferred views and their fluent response methods."""

from __future__ import annotations
from types import MappingProxyType, SimpleNamespace
from orionis.background.task import BackgroundTask
from orionis.http.adapters.response.asgi import ASGIResponseAdapter
from orionis.http.adapters.response.rsgi import RSGIResponseAdapter
from orionis.http.enums.status import HTTPStatus
from orionis.http.factory import response
from orionis.http.responses import HTMLResponse
from orionis.support.facades.view import View
from orionis.test import TestCase
from orionis.view.factory import ViewFactory
from orionis.view.pending import PendingView
from tests.http.test_support import replace_attribute


class _RecordingEngine:
    """Record template context without using application templates."""

    def __init__(self) -> None:
        """Start with no rendering work performed.

        Returns
        -------
        None
            No return value.
        """
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def render(self, template: str, context: dict[str, object]) -> str:
        """Record the render request and return fixed HTML.

        Parameters
        ----------
        template : str
            Requested template name.
        context : dict[str, object]
            Template variables forwarded by the view factory.

        Returns
        -------
        str
            Rendered HTML for transport assertions.
        """
        self.calls.append((template, context))
        return "<h1>Unauthorized</h1>"


class _RecordedBackground(BackgroundTask):
    """Record task execution without application logging dependencies."""

    def __init__(self, events: list[str]) -> None:
        """Retain the transport's event journal.

        Parameters
        ----------
        events : list[str]
            Event journal shared with the response transport.

        Returns
        -------
        None
            No return value.
        """
        super().__init__(events.append, "background")
        self.events = events

    async def __call__(self) -> None:
        """Record that the transport executed its background task.

        Returns
        -------
        None
            No return value.
        """
        self.events.append("background")


class TestViewResponseOptions(TestCase):
    """Exercise both public factories through the real pinned view facade."""

    def setUp(self) -> None:
        """Bind an isolated view factory and restore the facade after each test.

        Returns
        -------
        None
            No return value.
        """
        self.engine = _RecordingEngine()
        self.factory = ViewFactory(self.engine)
        self.enterContext(replace_attribute(View, "_pinned_instance", self.factory))

    async def testFactoriesKeepRenderingDeferredAndSeparateHttpOptions(self) -> None:
        """Carry response options independently from ordinary template variables.

        Returns
        -------
        None
            No return value.
        """
        for make in (View.make, response.view):
            with self.subTest(factory=make.__qualname__):
                self.engine.calls.clear()
                events = []
                task = _RecordedBackground(events)
                pending = make(
                    "errors.401",
                    status_code=HTTPStatus.UNAUTHORIZED,
                    headers=MappingProxyType({"Cache-Control": "no-store"}),
                    background=task,
                    ip="127.0.0.1",
                )

                self.assertIsInstance(pending, PendingView)
                self.assertEqual(self.engine.calls, [])
                html = await pending

                self.assertIsInstance(html, HTMLResponse)
                self.assertEqual(html.getStatusCode(), HTTPStatus.UNAUTHORIZED)
                self.assertEqual(html.getHeader("cache-control"), ["no-store"])
                self.assertEqual(html.getHeader("x-orionis-render"), ["SSR"])
                self.assertEqual(
                    html.getHeader("content-type"),
                    ["text/html; charset=utf-8"],
                )
                self.assertIs(html.background, task)
                self.assertEqual(events, [])
                self.assertEqual(
                    self.engine.calls,
                    [("errors.401", {"ip": "127.0.0.1"})],
                )

    async def testExplicitContextRetainsReservedNamesAndKeywordPrecedence(self) -> None:
        """Allow reserved response names as template data without mutating callers.

        Returns
        -------
        None
            No return value.
        """
        variables = {
            "status_code": "template status",
            "headers": "template headers",
            "background": "template background",
            "context": "template context",
            "ip": "old",
        }
        for make in (View.make, response.view):
            with self.subTest(factory=make.__qualname__):
                html = await make(
                    "errors.401",
                    status_code=401,
                    context=MappingProxyType(variables),
                    ip="127.0.0.1",
                )
                self.assertEqual(html.getStatusCode(), HTTPStatus.UNAUTHORIZED)
                self.assertEqual(
                    self.engine.calls[-1],
                    ("errors.401", {**variables, "ip": "127.0.0.1"}),
                )
                self.assertEqual(variables["ip"], "old")

    async def testHeaderOverridesAreCaseInsensitiveAndDoNotMutateInputs(self) -> None:
        """Preserve custom SSR and content types without duplicate defaults.

        Returns
        -------
        None
            No return value.
        """
        headers = {
            "x-orionis-render": "custom",
            "CONTENT-TYPE": "text/html; charset=us-ascii",
        }
        html = await View.make("errors.401", headers=MappingProxyType(headers))

        self.assertEqual(html.getHeader("X-Orionis-Render"), ["custom"])
        self.assertEqual(
            html.getHeader("content-type"),
            ["text/html; charset=us-ascii"],
        )
        self.assertEqual(
            headers,
            {
                "x-orionis-render": "custom",
                "CONTENT-TYPE": "text/html; charset=us-ascii",
            },
        )

    async def testFluentOptionsOverrideArgumentsInMutationOrder(self) -> None:
        """Replay new and existing response methods in the order supplied.

        Returns
        -------
        None
            No return value.
        """
        original = _RecordedBackground([])
        replacement = _RecordedBackground([])
        pending = response.view(
            "errors.401",
            status_code=400,
            headers={"X-Step": "argument", "X-Keep": "retained"},
            background=original,
        )
        self.assertIs(pending.withStatusCode(401), pending)
        self.assertIs(pending.withBackground(replacement), pending)
        self.assertIs(
            pending.withHeaders(MappingProxyType({"x-step": "fluent"})),
            pending,
        )
        pending.setHeader("X-Step", "replaced").addHeader("X-Step", "appended")
        pending.withStatusCode(403).withCookie("notice", "visible")
        self.assertEqual(self.engine.calls, [])

        html = await pending

        self.assertEqual(html.getStatusCode(), HTTPStatus.FORBIDDEN)
        self.assertEqual(html.getHeader("x-step"), ["replaced", "appended"])
        self.assertEqual(html.getHeader("x-keep"), ["retained"])
        self.assertTrue(html.hasHeader("set-cookie"))
        self.assertIs(html.background, replacement)

    async def testFluentBackgroundCanClearTheConstructorTask(self) -> None:
        """Allow a later fluent call to cancel the configured background task.

        Returns
        -------
        None
            No return value.
        """
        html = await View.make(
            "errors.401",
            background=_RecordedBackground([]),
        ).withBackground(None)

        self.assertIsNone(html.background)

    async def testRepeatedAwaitCreatesIndependentResponseHeaders(self) -> None:
        """Render each await independently without leaking response mutations.

        Returns
        -------
        None
            No return value.
        """
        pending = response.view(
            "errors.401",
            status_code=401,
            headers={"X-Shared": "initial"},
        ).withHeaders({"X-Queued": "value"})
        first = await pending
        first.setHeader("X-Shared", "changed")
        first.removeHeader("X-Queued")
        second = await pending

        self.assertIsNot(first, second)
        self.assertEqual(second.getStatusCode(), HTTPStatus.UNAUTHORIZED)
        self.assertEqual(second.getHeader("x-shared"), ["initial"])
        self.assertEqual(second.getHeader("x-queued"), ["value"])
        self.assertEqual(len(self.engine.calls), 2)

    async def testInvalidConstructorOptionsKeepResponseValidationErrors(self) -> None:
        """Expose response validation errors without treating them as template errors.

        Returns
        -------
        None
            No return value.
        """
        cases = (
            ({"status_code": "401"}, TypeError),
            ({"status_code": 99}, ValueError),
            ({"status_code": 600}, ValueError),
            ({"headers": ["not a mapping"]}, TypeError),
            ({"background": object()}, TypeError),
        )
        for options, error in cases:
            with self.subTest(options=options):
                pending = response.view("errors.401", **options)
                with self.assertRaises(error):
                    await pending

    async def testInvalidFluentOptionsAreValidatedWhenAwaited(self) -> None:
        """Keep queued method validation at the deferred rendering boundary.

        Returns
        -------
        None
            No return value.
        """
        cases = (
            ("withStatusCode", "401", TypeError),
            ("withStatusCode", 600, ValueError),
            ("withHeaders", ["not a mapping"], TypeError),
            ("withBackground", object(), TypeError),
        )
        for method, value, error in cases:
            with self.subTest(method=method, value=value):
                pending = View.make("errors.401")
                getattr(pending, method)(value)
                with self.assertRaises(error):
                    await pending

    async def testTransportsSendConfiguredStatusAndRunBackgroundAfterBody(self) -> None:
        """Deliver the configured view before running its selected background task.

        Returns
        -------
        None
            No return value.
        """
        for transport in ("asgi", "rsgi"):
            with self.subTest(transport=transport):
                events: list[str] = []
                html = await response.view(
                    "errors.401",
                    status_code=401,
                    headers={"Cache-Control": "no-store"},
                    background=_RecordedBackground(events),
                )
                self.assertEqual(events, [])
                request = SimpleNamespace(method=lambda: "GET")

                async def send(
                    message: dict[str, object],
                    journal: list[str] = events,
                ) -> None:
                    """Record the ASGI body and verify the emitted start metadata."""
                    if message["type"] == "http.response.start":
                        self.assertEqual(message["status"], HTTPStatus.UNAUTHORIZED)
                        self.assertIn(
                            (b"cache-control", b"no-store"),
                            message["headers"],
                        )
                    else:
                        self.assertEqual(message["body"], b"<h1>Unauthorized</h1>")
                        journal.append("body")

                def response_bytes(
                    status: int,
                    headers: list[tuple[str, str]],
                    body: bytes,
                    journal: list[str] = events,
                ) -> None:
                    """Record the RSGI body and verify its status and headers."""
                    self.assertEqual(status, HTTPStatus.UNAUTHORIZED)
                    self.assertIn(("cache-control", "no-store"), headers)
                    self.assertEqual(body, b"<h1>Unauthorized</h1>")
                    journal.append("body")

                if transport == "asgi":
                    await ASGIResponseAdapter().send(request, html, None, send)
                else:
                    await RSGIResponseAdapter().send(
                        request,
                        html,
                        SimpleNamespace(response_bytes=response_bytes),
                    )

                self.assertEqual(events, ["body", "background"])
