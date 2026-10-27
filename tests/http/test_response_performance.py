from __future__ import annotations
from functools import partial
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import TYPE_CHECKING
from orionis.http.factory import response
from orionis.http.responses import (
    EventStreamResponse,
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from orionis.test import TestCase
from tests.http.test_support import replace_attribute

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from os import stat_result
    from orionis.background.task import BackgroundTask

class _BodyBytes(bytes):
    __slots__ = ()

class _HookTextResponse(PlainTextResponse):
    """Record the header extension points used during subclass construction."""

    __slots__ = ("events",)

    def __init__(self) -> None:
        """Create a text response and retain its constructor hook calls.

        Returns
        -------
        None
            Initialize the response and hook recorder.
        """
        self.events: list[tuple[str, str]] = []
        super().__init__("body")

    def hasHeader(self, key: str) -> bool:
        """Record a header presence check.

        Parameters
        ----------
        key : str
            Header name checked by the constructor.

        Returns
        -------
        bool
            Whether the header is present.
        """
        self.events.append(("has", key))
        return super().hasHeader(key)

    def setHeader(self, key: str, value: str) -> None:
        """Record a header assignment.

        Parameters
        ----------
        key : str
            Header name assigned by the constructor.
        value : str
            Header value to store.

        Returns
        -------
        None
            Store the header using the parent implementation.
        """
        self.events.append(("set", key))
        super().setHeader(key, value)

class _HeaderHookResponse(Response):
    """Provide a hook recorder without adding conflicting response slots."""

    def __init__(
        self,
        content: object = None,
        status_code: int = 200,
        headers: Mapping[str, str] | None = None,
        media_type: str | None = None,
        background: BackgroundTask | None = None,
    ) -> None:
        """Initialize the response and its request-local hook history.

        Parameters
        ----------
        content : object
            Body or stream supplied by the concrete constructor.
        status_code : int
            Response status code.
        headers : Mapping[str, str] | None
            Caller-owned header mapping.
        media_type : str | None
            Response media type.
        background : BackgroundTask | None
            Optional completion task.

        Returns
        -------
        None
            Initialize independent response state and hook history.
        """
        self.events: list[tuple[str, str]] = []
        super().__init__(content, status_code, headers, media_type, background)

    def hasHeader(self, key: str) -> bool:
        """Record a header presence check.

        Parameters
        ----------
        key : str
            Header name to inspect.

        Returns
        -------
        bool
            Whether the header is present.
        """
        self.events.append(("has", key))
        return super().hasHeader(key)

    def setHeader(self, key: str, value: str) -> None:
        """Record a header assignment.

        Parameters
        ----------
        key : str
            Header name to assign.
        value : str
            Value to store.

        Returns
        -------
        None
            Store the header through the parent implementation.
        """
        self.events.append(("set", key))
        super().setHeader(key, value)

    def removeHeader(self, key: str) -> None:
        """Record a header removal.

        Parameters
        ----------
        key : str
            Header name to remove.

        Returns
        -------
        None
            Remove the header through the parent implementation.
        """
        self.events.append(("remove", key))
        super().removeHeader(key)

class _HookHTMLResponse(HTMLResponse, _HeaderHookResponse):
    __slots__ = ()

class _HookJSONResponse(JSONResponse, _HeaderHookResponse):
    __slots__ = ()

class _HookRedirectResponse(RedirectResponse, _HeaderHookResponse):
    __slots__ = ()

class _HookStreamingResponse(StreamingResponse, _HeaderHookResponse):
    __slots__ = ()

class _HookEventStreamResponse(EventStreamResponse, _HeaderHookResponse):
    __slots__ = ()

class _HookFileResponse(FileResponse, _HeaderHookResponse):
    __slots__ = ()

class _ObservedHeaders(dict[str, str]):
    __slots__ = ("truth_checks",)

    def __init__(self) -> None:
        """Prepare an empty mapping with an observable truth-value check.

        Returns
        -------
        None
            Initialize the counter and mapping.
        """
        super().__init__()
        self.truth_checks = 0

    def __bool__(self) -> bool:
        """Count each truth-value check.

        Returns
        -------
        bool
            Whether the mapping contains headers.
        """
        self.truth_checks += 1
        return len(self) > 0

class _MediaType(str):
    __slots__ = ()

def _response_factories(path: Path) -> dict[str, Callable[..., Response]]:
    """Bind representative constructors to their required inputs.

    Parameters
    ----------
    path : Path
        Existing file used by the file response.

    Returns
    -------
    dict[str, Callable[..., Response]]
        Fresh-response constructors accepting optional header arguments.
    """
    return {
        "html": partial(HTMLResponse, "body"),
        "json": partial(JSONResponse, {"id": 7}),
        "redirect": partial(RedirectResponse, "/next"),
        "stream": partial(
            StreamingResponse, (b"body",), media_type="text/plain",
        ),
        "sse": partial(EventStreamResponse, ("body",)),
        "file": partial(
            FileResponse, path, media_type="text/plain", filename="data.txt",
        ),
    }

class TestResponseResources(TestCase):

    def testBuiltInMetadataKeepsHeaderOrderAndOwnership(self) -> None:
        """Keep default metadata ordered and isolated for every response type.

        Returns
        -------
        None
            Verify fresh header stores, stable output and caller ownership.
        """
        expected = {
            "html": [("content-type", "text/html; charset=utf-8")],
            "json": [("content-type", "application/json; charset=utf-8")],
            "redirect": [
                ("location", "/next"),
                ("content-type", "text/plain; charset=utf-8"),
            ],
            "stream": [("content-type", "text/plain; charset=utf-8")],
            "sse": [
                ("content-type", "text/event-stream; charset=utf-8"),
                ("cache-control", "no-cache"), ("x-accel-buffering", "no"),
            ],
            "file": [
                ("content-type", "text/plain; charset=utf-8"),
                ("content-length", "4"),
                ("content-disposition", 'attachment; filename="data.txt"'),
            ],
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "data.txt"
            path.write_bytes(b"data")
            for name, factory in _response_factories(path).items():
                for headers in (None, {}, MappingProxyType({}), _ObservedHeaders()):
                    with self.subTest(response=name, headers=type(headers)):
                        first = factory(headers=headers)
                        second = factory(headers=headers)
                        self.assertIsNot(first, second)
                        self.assertEqual(first.getStringHeaders(), expected[name])
                        self.assertEqual(second.getStringHeaders(), expected[name])
                        retained = first.getRawHeaders()
                        first.getHeader("content-type").append("changed")
                        first.setCookie("owner", "first")
                        second.getRawHeaders().clear()
                        self.assertEqual(second.getStringHeaders(), expected[name])
                        self.assertEqual(retained[0][0], expected[name][0][0].encode())
                        if headers is not None:
                            self.assertEqual(headers, {})
                        if isinstance(headers, _ObservedHeaders):
                            self.assertEqual(headers.truth_checks, 2)

    def testBuiltInMetadataPreservesCustomHeaders(self) -> None:
        """Preserve duplicate names, overrides and caller mappings.

        Returns
        -------
        None
            Assert exact header ordering and type-specific metadata precedence.
        """
        original = {
            "X-First": "keep", "CONTENT-TYPE": "custom/one",
            "content-type": "custom/two", "Location": "/old",
            "Content-Length": "999", "Content-Disposition": "inline",
            "Cache-Control": "private", "X-Accel-Buffering": "yes",
        }
        with TemporaryDirectory() as directory:
            path = Path(directory) / "data.txt"
            path.write_bytes(b"data")
            for name, factory in _response_factories(path).items():
                with self.subTest(response=name):
                    headers = dict(original)
                    result = factory(headers=MappingProxyType(headers))
                    expected = [
                        ("x-first", "keep"), ("content-type", "custom/one"),
                        ("content-type", "custom/two"),
                        ("location", "/next" if name == "redirect" else "/old"),
                        ("content-length", "4" if name == "file" else "999"),
                        (
                            "content-disposition",
                            'attachment; filename="data.txt"' if name == "file"
                            else "inline",
                        ),
                        ("cache-control", "private"), ("x-accel-buffering", "yes"),
                    ]
                    if name == "sse":
                        expected = [
                            pair for pair in expected if pair[0] != "content-length"
                        ]
                    self.assertEqual(result.getStringHeaders(), expected)
                    self.assertEqual(headers, original)

    def testOtherResponseSubclassesPreserveHeaderHooks(self) -> None:
        """Keep constructor hooks and their ordering outside concrete fast paths.

        Returns
        -------
        None
            Verify header presence, assignment and removal hooks for all types.
        """
        content_type = [("has", "content-type"), ("set", "content-type")]
        with TemporaryDirectory() as directory:
            path = Path(directory) / "data.txt"
            path.write_bytes(b"data")
            factories = {
                "html": partial(_HookHTMLResponse, "body"),
                "json": partial(_HookJSONResponse, {"id": 7}),
                "redirect": partial(_HookRedirectResponse, "/next"),
                "stream": partial(
                    _HookStreamingResponse, (b"body",), media_type="text/plain",
                ),
                "sse": partial(_HookEventStreamResponse, ("body",)),
                "file": partial(
                    _HookFileResponse, path, media_type="text/plain",
                    filename="data.txt",
                ),
            }
            expected = {
                "html": content_type, "json": content_type,
                "redirect": [("set", "location"), *content_type],
                "stream": content_type,
                "sse": [
                    *content_type,
                    ("has", "cache-control"), ("set", "cache-control"),
                    ("has", "x-accel-buffering"), ("set", "x-accel-buffering"),
                    ("remove", "content-length"),
                ],
                "file": [
                    *content_type, ("set", "content-length"),
                    ("set", "content-disposition"),
                ],
            }
            for name, factory in factories.items():
                with self.subTest(response=name):
                    result = factory()
                    self.assertEqual(result.events, expected[name])
                    self.assertEqual(
                        result.getStringHeaders(),
                        _response_factories(path)[name]().getStringHeaders(),
                    )

    def testOtherResponsesKeepHeaderEncodingLazy(self) -> None:
        """Reject invalid transport headers only when serializing them.

        Returns
        -------
        None
            Preserve constructor and mutation behavior for unencodable values.
        """
        with TemporaryDirectory() as directory:
            path = Path(directory) / "data.txt"
            path.write_bytes(b"data")
            for name, factory in _response_factories(path).items():
                with self.subTest(response=name):
                    result = factory(headers={"X-Name": "\u2603"})
                    result.setHeader("x-extra", "\u2603")
                    self.assertEqual(result.getHeader("x-name"), ["\u2603"])
                    with self.assertRaises(UnicodeEncodeError):
                        result.getRawHeaders()

    def testCustomContentTypeSkipsMediaTypeFormatting(self) -> None:
        """Avoid touching media-type formatting when a header already exists.

        Returns
        -------
        None
            Streams and files retain the lazy formatting boundary.
        """
        def unexpected_format(*_args: object) -> bool:
            """Reject a formatting call that should have been skipped.

            Parameters
            ----------
            *_args : object
                Arguments passed to the string prefix check.

            Returns
            -------
            bool
                No value is returned.

            Raises
            ------
            AssertionError
                If formatting is attempted despite a supplied Content-Type.
            """
            error_msg = "media type must not be formatted"
            raise AssertionError(error_msg)

        with TemporaryDirectory() as directory:
            path = Path(directory) / "data.txt"
            path.write_bytes(b"data")
            with replace_attribute(_MediaType, "startswith", unexpected_format):
                stream = StreamingResponse(
                    (), media_type=_MediaType("text/custom"),
                    headers={"Content-Type": "custom/type"},
                )
                file = FileResponse(
                    path, media_type=_MediaType("text/custom"),
                    headers={"Content-Type": "custom/type"},
                )
            self.assertEqual(stream.getHeader("content-type"), ["custom/type"])
            self.assertEqual(file.getHeader("content-type"), ["custom/type"])

    def testStreamSubclassesKeepHookLookupBeforeMediaFormatting(self) -> None:
        """Preserve method lookup order around user-defined media formatting.

        Returns
        -------
        None
            Streaming and file subclasses retain the original callback order.
        """
        events = []

        def read_attribute(instance: object, key: str) -> object:
            """Record header-method lookup before returning its bound value.

            Parameters
            ----------
            instance : object
                Response whose attribute is being read.
            key : str
                Requested attribute name.

            Returns
            -------
            object
                Attribute returned by the normal object lookup.
            """
            if key == "setHeader":
                events.append("lookup")
            return object.__getattribute__(instance, key)

        def check_prefix(value: str, prefix: str) -> bool:
            """Record the media-type prefix check.

            Parameters
            ----------
            value : str
                Media type being inspected.
            prefix : str
                Expected text-media prefix.

            Returns
            -------
            bool
                Whether the media type starts with the prefix.
            """
            events.append("format")
            return str.startswith(value, prefix)

        with TemporaryDirectory() as directory:
            path = Path(directory) / "data.txt"
            path.write_bytes(b"data")
            factories = (
                (_HookStreamingResponse, (b"body",), {}, ["lookup", "format"]),
                (
                    _HookFileResponse, path, {"filename": "data.txt"},
                    ["lookup", "format", "lookup", "lookup"],
                ),
            )
            for response_type, content, options, expected in factories:
                with (
                    self.subTest(response=response_type),
                    replace_attribute(
                        response_type, "__getattribute__", read_attribute,
                    ),
                    replace_attribute(_MediaType, "startswith", check_prefix),
                ):
                    events.clear()
                    response_type(
                        content, media_type=_MediaType("text/custom"), **options,
                    )
                    self.assertEqual(events, expected)

    def testTextConstructionPreservesSubclassHeaderHooks(self) -> None:
        """Retain constructor extension points outside the concrete fast path.

        Returns
        -------
        None
            Assert that subclasses still observe both header operations.
        """
        result = _HookTextResponse()
        self.assertEqual(result.events, [
            ("has", "content-type"), ("set", "content-type"),
        ])
        self.assertEqual(result.getBody(), b"body")

    def testTextHeadersRemainIndependentForEmptyMappings(self) -> None:
        """Keep default headers and transport results owned by each response.

        Returns
        -------
        None
            Verify fresh responses and isolation of mutable header accessors.
        """
        for headers in (None, {}, MappingProxyType({})):
            with self.subTest(headers=headers):
                first = response.text("first", headers=headers)
                second = response.text("second", headers=headers)
                self.assertIsNot(first, second)
                first.getHeader("content-type").append("changed")
                self.assertEqual(second.getHeader("content-type"), [
                    "text/plain; charset=utf-8",
                ])
                second.getRawHeaders().clear()
                self.assertEqual(second.getRawHeaders(), [
                    (b"content-type", b"text/plain; charset=utf-8"),
                ])
                self.assertEqual(first.getBody(), b"first")
                self.assertEqual(second.getBody(), b"second")

    def testTextHeaderEncodingRemainsLazy(self) -> None:
        """Reject an unencodable header at serialization rather than mutation.

        Returns
        -------
        None
            Preserve the point at which invalid transport headers raise.
        """
        result = response.text("body")
        result.setHeader("x-name", "\u2603")
        self.assertEqual(result.getStringHeaders()[-1], ("x-name", "\u2603"))
        with self.assertRaises(UnicodeEncodeError):
            result.getRawHeaders()

    def testFileConstructionUsesOneStat(self) -> None:
        """Read file type and size from the same metadata result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with TemporaryDirectory() as directory:
            path = Path(directory) / "file.txt"
            path.write_bytes(b"data")
            stat = Path.stat
            calls = []

            def record_stat(
                file_path: Path, *, follow_symlinks: bool = True,
            ) -> stat_result:
                """
                Record the metadata lookup and return the actual file status.

                Parameters
                ----------
                file_path : Path
                    Path of the file to inspect or open.
                follow_symlinks : bool
                    Whether metadata follows symbolic links.

                Returns
                -------
                stat_result
                    Metadata returned by the filesystem.
                """
                calls.append(file_path)
                return stat(file_path, follow_symlinks=follow_symlinks)

            with replace_attribute(Path, "stat", record_stat):
                response = FileResponse(path, media_type="text/plain")
            self.assertEqual(calls, [path])
            self.assertEqual(response.getFileSize(), 4)

    def testFileRejectsInvalidChunkSizes(self) -> None:
        """Reject chunk sizes that cannot produce a bounded byte stream.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with TemporaryDirectory() as directory:
            path = Path(directory) / "file.txt"
            path.write_bytes(b"data")
            for chunk_size in (0, -1):
                with self.subTest(chunk_size=chunk_size), self.assertRaises(ValueError):
                    FileResponse(path, chunk_size=chunk_size)
            with self.assertRaises(TypeError):
                FileResponse(path, chunk_size="invalid")

    def testBytesSubclassIsPreserved(self) -> None:
        """Treat byte subclasses as encoded response bodies.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        content = _BodyBytes(b"raw")
        self.assertIs(Response(content).getBody(), content)

    async def testSyncStreamAcceptsBytesSubclasses(self) -> None:
        """Preserve byte subclass chunks in synchronous streams.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        content = _BodyBytes(b"raw")
        response = StreamingResponse([content])
        chunks = [chunk async for chunk in response.getStream()]
        self.assertIs(chunks[0], content)
