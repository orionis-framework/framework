from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import ClassVar
from orionis.http import factory as factory_module
from orionis.http.enums.status import HTTPStatus
from orionis.http.factory import ResponseFactory, response
from orionis.http.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from orionis.test import TestCase


class _Money:
    """Domain value object that no JSON encoder handles natively."""

    __slots__ = ("amount",)

    def __init__(self, amount: str) -> None:
        """
        Store the raw amount as text.

        Parameters
        ----------
        amount : str
            Amount rendered by the custom encoder.
        """
        self.amount = amount


class _StubPendingView:
    """Stand-in for the pending view returned by the view facade."""

    __slots__ = ("context", "template")

    def __init__(self, template: str, context: dict[str, object]) -> None:
        """
        Record the rendering intent without touching the engine.

        Parameters
        ----------
        template : str
            Template name requested by the factory.
        context : dict[str, object]
            Template variables forwarded by the factory.
        """
        self.template = template
        self.context = context


class _StubViewFacade:
    """Facade double capturing the arguments the factory forwards."""

    calls: ClassVar[list[tuple[str, dict[str, object]]]] = []

    @classmethod
    def make(cls, template: str, **context: object) -> _StubPendingView:
        """
        Return a pending view double and record the call.

        Parameters
        ----------
        template : str
            Template name requested by the factory.
        **context : object
            Template variables forwarded by the factory.

        Returns
        -------
        _StubPendingView
            Double carrying the recorded rendering intent.
        """
        cls.calls.append((template, context))
        return _StubPendingView(template, context)


class TestResponseFactoryView(TestCase):

    def setUp(self) -> None:
        """
        Install a view facade double for the duration of the test.

        Validates the factory delegation without booting the template
        engine or touching the filesystem.
        """
        _StubViewFacade.calls = []
        self._original_facade = factory_module.View
        factory_module.View = _StubViewFacade

    def tearDown(self) -> None:
        """
        Restore the real view facade after the test.

        Validates that the swap never leaks into other test cases.
        """
        factory_module.View = self._original_facade

    def testViewDelegatesToTheFacade(self) -> None:
        """
        Forward the template name and context to the view facade.

        Validates that controllers can render a template through the
        shared response factory.
        """
        result = response.view("users.index", total=2)
        self.assertIsInstance(result, _StubPendingView)
        self.assertEqual(_StubViewFacade.calls, [("users.index", {"total": 2})])

    def testViewIsNotAwaitedByTheFactory(self) -> None:
        """
        Return the pending view untouched so it stays chainable.

        Validates that mutators such as ``withErrors()`` can be chained on
        the value returned by ``view()``.
        """
        result = response.view("auth.login")
        self.assertEqual(result.template, "auth.login")
        self.assertEqual(result.context, {})


class TestResponseFactoryHtml(TestCase):

    def testHtmlUsesSaneDefaults(self) -> None:
        """
        Build an empty ``200`` HTML response by default.

        Validates the shortest call form used by controllers that render
        markup built elsewhere.
        """
        result = response.html()
        self.assertIsInstance(result, HTMLResponse)
        self.assertEqual(result.getStatusCode(), 200)
        self.assertEqual(result.getBody(), b"")

    def testHtmlForwardsEveryArgument(self) -> None:
        """
        Forward content, status code and headers to the response.

        Validates that the factory adds no behaviour of its own beyond
        constructing the right response class.
        """
        result = response.html(
            "<p>hi</p>",
            HTTPStatus.CREATED,
            {"x-source": "factory"},
        )
        self.assertEqual(result.getBody(), b"<p>hi</p>")
        self.assertEqual(result.getStatusCode(), 201)
        self.assertEqual(result.getHeader("x-source"), ["factory"])


class TestResponseFactoryJson(TestCase):

    def testJsonSerialisesTheContent(self) -> None:
        """
        Serialise the payload and advertise the JSON content type.

        Validates the default path used by API controllers.
        """
        result = response.json({"ok": True})
        self.assertIsInstance(result, JSONResponse)
        self.assertEqual(result.getBody(), b'{"ok":true}')
        self.assertEqual(
            result.getHeader("content-type"),
            ["application/json; charset=utf-8"],
        )

    def testJsonForwardsFormattingOptions(self) -> None:
        """
        Forward the pretty-printing options to the response.

        Validates that indentation requested at the call site reaches the
        serializer instead of being silently dropped.
        """
        result = response.json({"a": 1}, indent=2)
        self.assertEqual(result.getBody(), b'{\n  "a": 1\n}')

    def testJsonForwardsTheCustomEncoder(self) -> None:
        """
        Use the caller-supplied encoder for unsupported types.

        Validates that domain objects can be serialised without changing
        the framework encoder.
        """
        result = response.json(
            {"money": _Money("12.50")},
            default=lambda value: f"custom:{value.amount}",
        )
        self.assertEqual(result.getBody(), b'{"money":"custom:12.50"}')

    def testJsonForwardsStatusAndHeaders(self) -> None:
        """
        Forward the status code and extra headers untouched.

        Validates that error payloads can be produced through the same
        helper as successful ones.
        """
        result = response.json({"error": "nope"}, 422, {"x-trace": "abc"})
        self.assertEqual(result.getStatusCode(), 422)
        self.assertEqual(result.getHeader("x-trace"), ["abc"])


class TestResponseFactoryText(TestCase):

    def testTextUsesSaneDefaults(self) -> None:
        """
        Build an empty ``200`` plain-text response by default.

        Validates the shortest call form used for health-check endpoints.
        """
        result = response.text()
        self.assertIsInstance(result, PlainTextResponse)
        self.assertEqual(result.getBody(), b"")
        self.assertEqual(
            result.getHeader("content-type"),
            ["text/plain; charset=utf-8"],
        )

    def testTextForwardsEveryArgument(self) -> None:
        """
        Forward content, status code and headers to the response.

        Validates that plain-text errors keep their status code.
        """
        result = response.text("gone", 410, {"x-reason": "expired"})
        self.assertEqual(result.getBody(), b"gone")
        self.assertEqual(result.getStatusCode(), 410)
        self.assertEqual(result.getHeader("x-reason"), ["expired"])


class TestResponseFactoryRedirect(TestCase):

    def testRedirectDefaultsToFound(self) -> None:
        """
        Redirect with ``302`` and the target in the location header.

        Validates the default used after a successful form submission.
        """
        result = response.redirect("/login")
        self.assertIsInstance(result, RedirectResponse)
        self.assertEqual(result.getStatusCode(), 302)
        self.assertEqual(result.getHeader("location"), ["/login"])

    def testRedirectForwardsStatusAndHeaders(self) -> None:
        """
        Forward a permanent status code and extra headers.

        Validates that ``301`` redirects can be produced through the same
        helper.
        """
        result = response.redirect("/new", 301, {"x-legacy": "yes"})
        self.assertEqual(result.getStatusCode(), 301)
        self.assertEqual(result.getHeader("x-legacy"), ["yes"])


class TestResponseFactoryStream(TestCase):

    async def testStreamAcceptsASynchronousIterable(self) -> None:
        """
        Adapt a synchronous byte iterable into a streaming response.

        Validates that generators producing chunks can be returned
        directly by a controller.
        """
        result = response.stream([b"a", b"b"], media_type="text/csv")
        self.assertIsInstance(result, StreamingResponse)
        chunks = [chunk async for chunk in result.getStream()]
        self.assertEqual(chunks, [b"a", b"b"])

    def testStreamForwardsStatusAndHeaders(self) -> None:
        """
        Forward the status code, headers and media type.

        Validates that a streamed export can advertise its own content
        type and disposition.
        """
        result = response.stream(
            [b"chunk"],
            206,
            {"x-partial": "1"},
            "application/octet-stream",
        )
        self.assertEqual(result.getStatusCode(), 206)
        self.assertEqual(result.getHeader("x-partial"), ["1"])
        self.assertEqual(result.getMediaType(), "application/octet-stream")


class _FileFactoryTestCase(TestCase):
    """Base case providing a temporary file on disk."""

    def setUp(self) -> None:
        """
        Create a temporary file served by the file helpers.

        Validates the file responses against real filesystem metadata
        instead of stubbed sizes.
        """
        self._tmp = TemporaryDirectory()
        self._file = Path(self._tmp.name) / "report.txt"
        self._file.write_bytes(b"payload")

    def tearDown(self) -> None:
        """
        Remove the temporary directory after the test.

        Validates that the suite leaves no artefacts behind.
        """
        self._tmp.cleanup()


class TestResponseFactoryFile(_FileFactoryTestCase):

    def testFileGuessesTheMediaType(self) -> None:
        """
        Serve a file and infer its media type from the extension.

        Validates that controllers do not need to repeat the MIME type
        for well-known extensions.
        """
        result = response.file(self._file)
        self.assertIsInstance(result, FileResponse)
        self.assertEqual(result.getMediaType(), "text/plain")
        self.assertEqual(result.getFileSize(), len(b"payload"))

    def testFileForwardsEveryArgument(self) -> None:
        """
        Forward status, headers, media type, filename and chunk size.

        Validates that a download can be tuned without bypassing the
        factory.
        """
        result = response.file(
            str(self._file),
            206,
            {"x-range": "bytes"},
            "application/pdf",
            "invoice.pdf",
            8,
        )
        self.assertEqual(result.getStatusCode(), 206)
        self.assertEqual(result.getHeader("x-range"), ["bytes"])
        self.assertEqual(result.getMediaType(), "application/pdf")
        self.assertEqual(
            result.getHeader("content-disposition"),
            ['attachment; filename="invoice.pdf"'],
        )


class TestResponseFactoryDownload(_FileFactoryTestCase):

    def testDownloadFallsBackToTheFileName(self) -> None:
        """
        Advertise the file name when no override is supplied.

        Validates that the browser saves the attachment under its
        original name.
        """
        result = response.download(self._file)
        self.assertEqual(
            result.getHeader("content-disposition"),
            ['attachment; filename="report.txt"'],
        )

    def testDownloadHonoursTheRequestedName(self) -> None:
        """
        Advertise the caller-supplied attachment name.

        Validates that a generated export can be renamed for the user.
        """
        result = response.download(
            self._file,
            "summary.txt",
            {"x-export": "1"},
            "text/plain",
        )
        self.assertEqual(
            result.getHeader("content-disposition"),
            ['attachment; filename="summary.txt"'],
        )
        self.assertEqual(result.getHeader("x-export"), ["1"])
        self.assertEqual(result.getMediaType(), "text/plain")


class TestResponseFactoryBareResponses(TestCase):

    def testNoContentDefaultsToStatus204(self) -> None:
        """
        Build an empty ``204`` response by default.

        Validates the canonical answer of a successful delete endpoint.
        """
        result = response.noContent()
        self.assertIsInstance(result, Response)
        self.assertEqual(result.getStatusCode(), 204)
        self.assertEqual(result.getBody(), b"")

    def testNoContentForwardsStatusAndHeaders(self) -> None:
        """
        Forward an alternative empty status code and headers.

        Validates that ``304`` style responses reuse the same helper.
        """
        result = response.noContent(304, {"etag": "abc"})
        self.assertEqual(result.getStatusCode(), 304)
        self.assertEqual(result.getHeader("etag"), ["abc"])

    def testMakeBuildsABareResponse(self) -> None:
        """
        Build a response with full control over content and media type.

        Validates the escape hatch used when no specialised helper fits.
        """
        result = response.make("raw", 201, {"x-kind": "bare"}, "text/csv")
        self.assertEqual(result.getBody(), b"raw")
        self.assertEqual(result.getStatusCode(), 201)
        self.assertEqual(result.getHeader("x-kind"), ["bare"])
        self.assertEqual(result.getMediaType(), "text/csv")

    def testMakeDefaultsToAnEmptyOkResponse(self) -> None:
        """
        Build an empty ``200`` response when nothing is supplied.

        Validates that the helper is safe to call without arguments.
        """
        result = response.make()
        self.assertEqual(result.getBody(), b"")
        self.assertEqual(result.getStatusCode(), 200)
        self.assertIsNone(result.getMediaType())


class TestResponseFactoryInstance(TestCase):

    def testFactoryIsStateless(self) -> None:
        """
        Keep the shared factory free of per-instance state.

        Validates that importing the module-level instance is safe from
        concurrently handled requests.
        """
        self.assertEqual(ResponseFactory.__slots__, ())
        self.assertFalse(hasattr(response, "__dict__"))

    def testModuleLevelInstanceIsAFactory(self) -> None:
        """
        Expose a ready-to-use factory instance at module level.

        Validates the import shape used by every controller.
        """
        self.assertIsInstance(response, ResponseFactory)

    def testEveryHelperReturnsAResponseSubclass(self) -> None:
        """
        Return a response object from every non-view helper.

        Validates that handlers annotated with ``HttpResponse`` accept the
        output of any factory helper.
        """
        built: list[Response] = [
            response.html(),
            response.json({}),
            response.text(),
            response.redirect("/"),
            response.stream([b""]),
            response.noContent(),
            response.make(),
        ]
        self.assertTrue(all(isinstance(item, Response) for item in built))
