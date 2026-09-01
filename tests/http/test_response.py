from __future__ import annotations
import asyncio
from datetime import UTC, date, datetime, time, timedelta, timezone
from decimal import Decimal
from enum import Enum
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from typing import TYPE_CHECKING
from uuid import UUID
from orionis.background.task import BackgroundTask
from orionis.http.enums.status import HTTPStatus
from orionis.http.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    PlainTextResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from orionis.session.flash import ERRORS_KEY, OLD_INPUT_KEY
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

_CREDENTIAL_FIELD: str = "password"


class _Colour(Enum):
    """Enumeration used to exercise the JSON fallback encoder."""

    RED = "red"


class _Opaque:
    """Object that no JSON encoder in the framework knows how to render."""

    __slots__ = ()


async def _async_chunks() -> AsyncIterator[bytes]:
    """
    Yield two byte chunks asynchronously.

    Returns
    -------
    AsyncIterator[bytes]
        Asynchronous iterator producing the streamed chunks.
    """
    yield b"first"
    yield b"second"


async def _drain(stream: AsyncIterator[bytes]) -> list[bytes]:
    """
    Collect every chunk produced by an asynchronous stream.

    Parameters
    ----------
    stream : AsyncIterator[bytes]
        Stream attached to a response.

    Returns
    -------
    list[bytes]
        Chunks in the order they were produced.
    """
    return [chunk async for chunk in stream]


class TestResponseConstruction(TestCase):

    def testRejectsANonIntegerStatusCode(self) -> None:
        """
        Reject a status code that is not an integer.

        Validates that a typo in a handler surfaces immediately instead of
        producing a malformed response line.
        """
        with self.assertRaises(TypeError):
            Response(status_code="200")  # type: ignore[arg-type]

    def testRejectsAStatusCodeBelowTheHttpRange(self) -> None:
        """
        Reject a status code lower than ``100``.

        Validates the lower bound of the accepted status range.
        """
        with self.assertRaises(ValueError):
            Response(status_code=99)

    def testRejectsAStatusCodeAboveTheHttpRange(self) -> None:
        """
        Reject a status code greater than ``599``.

        Validates the upper bound of the accepted status range.
        """
        with self.assertRaises(ValueError):
            Response(status_code=600)

    def testAcceptsAStatusEnumMember(self) -> None:
        """
        Accept an ``HTTPStatus`` member as the status code.

        Validates that the enum used across the framework is usable
        wherever a plain integer is.
        """
        self.assertEqual(
            Response(status_code=HTTPStatus.NOT_FOUND).getStatusCode(),
            404,
        )

    def testRejectsHeadersThatAreNotAMapping(self) -> None:
        """
        Reject a header container that is not a mapping.

        Validates that a list of pairs is refused instead of being partly
        consumed.
        """
        with self.assertRaises(TypeError):
            Response(headers=[("a", "b")])  # type: ignore[arg-type]

    def testAcceptsAnyMappingImplementation(self) -> None:
        """
        Accept any mapping type as the header container.

        Validates that immutable mappings coming from configuration are
        usable without conversion.
        """
        result = Response(headers=MappingProxyType({"X-Source": "config"}))
        self.assertEqual(result.getHeader("x-source"), ["config"])

    def testIgnoresAnEmptyHeaderMapping(self) -> None:
        """
        Leave the header store empty when no header is supplied.

        Validates that the constructor allocates nothing for the common
        header-less response.
        """
        self.assertEqual(Response(headers={}).getStringHeaders(), [])

    def testRejectsABackgroundThatIsNotATask(self) -> None:
        """
        Reject a background value that is not a background task.

        Validates that a bare callable cannot be scheduled by mistake.
        """
        with self.assertRaises(TypeError):
            Response(background=lambda: None)  # type: ignore[arg-type]

    def testAcceptsABackgroundTask(self) -> None:
        """
        Store a background task for later execution.

        Validates the wiring used to run work after the response is sent.
        """
        task = BackgroundTask(lambda: None)
        self.assertIs(Response(background=task).background, task)

    def testDetectsAnAsynchronousBodyAsAStream(self) -> None:
        """
        Treat asynchronously iterable content as a stream.

        Validates that a generator handed to the base response is never
        buffered into memory.
        """
        result = Response(content=_async_chunks())
        self.assertTrue(result.hasStream())
        self.assertIsNone(result.getBody())

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """
        Keep responses free of a per-instance dictionary.

        Validates the slot layout that keeps the request hot path cheap.
        """
        self.assertFalse(hasattr(Response(), "__dict__"))


class TestResponseRender(TestCase):

    def testRendersNoneAsAnEmptyBody(self) -> None:
        """
        Render a missing body as zero bytes.

        Validates the default used by empty responses such as ``204``.
        """
        self.assertEqual(Response().getBody(), b"")

    def testKeepsBytesUntouched(self) -> None:
        """
        Return byte content without copying it.

        Validates the fast path taken by pre-encoded payloads.
        """
        payload = b"already-bytes"
        self.assertIs(Response(content=payload).getBody(), payload)

    def testConvertsByteArrays(self) -> None:
        """
        Convert a mutable byte buffer into immutable bytes.

        Validates that later mutations of the buffer cannot alter the sent
        body.
        """
        self.assertEqual(Response(content=bytearray(b"buf")).getBody(), b"buf")

    def testConvertsMemoryViews(self) -> None:
        """
        Convert a memory view into immutable bytes.

        Validates support for zero-copy buffers produced by parsers.
        """
        self.assertEqual(Response(content=memoryview(b"view")).getBody(), b"view")

    def testEncodesStringsAsUtf8(self) -> None:
        """
        Encode textual content using the response charset.

        Validates that non-ASCII characters survive the round trip.
        """
        self.assertEqual(Response(content="ñ").getBody(), "ñ".encode())

    def testStringifiesAnyOtherContent(self) -> None:
        """
        Fall back to the textual representation of the content.

        Validates that numbers returned by a handler still produce a valid
        body instead of raising.
        """
        self.assertEqual(Response(content=42).getBody(), b"42")


class TestResponseHeaders(TestCase):

    def testAddHeaderCreatesTheEntry(self) -> None:
        """
        Create the header entry on the first write.

        Validates the common single-value header case.
        """
        result = Response()
        result.addHeader("X-Trace", "abc")
        self.assertEqual(result.getHeader("x-trace"), ["abc"])

    def testAddHeaderAppendsRepeatedValues(self) -> None:
        """
        Append repeated values under the same header name.

        Validates support for multi-value headers such as ``set-cookie``.
        """
        result = Response()
        result.addHeader("Set-Cookie", "a=1")
        result.addHeader("set-cookie", "b=2")
        self.assertEqual(result.getHeader("set-cookie"), ["a=1", "b=2"])

    def testConstructorMergesRepeatedHeaderNames(self) -> None:
        """
        Merge header names that differ only by case at construction time.

        Validates that the header store stays canonical and lowercase.
        """
        result = Response(headers={"X-A": "1", "x-a": "2"})
        self.assertEqual(result.getHeader("X-A"), ["1", "2"])

    def testSetHeaderReplacesEveryValue(self) -> None:
        """
        Replace all previous values of a header.

        Validates that ``setHeader`` is not an alias of ``addHeader``.
        """
        result = Response()
        result.addHeader("x-a", "1")
        result.setHeader("X-A", "2")
        self.assertEqual(result.getHeader("x-a"), ["2"])

    def testGetHeaderReturnsNoneWhenAbsent(self) -> None:
        """
        Report a missing header as ``None``.

        Validates the lookup contract used by the transport adapters.
        """
        self.assertIsNone(Response().getHeader("x-missing"))

    def testHasHeaderReportsPresence(self) -> None:
        """
        Report whether a header has been set.

        Validates the guard used before applying default content types.
        """
        result = Response(headers={"X-A": "1"})
        self.assertTrue(result.hasHeader("x-a"))
        self.assertFalse(result.hasHeader("x-b"))

    def testRemoveHeaderIsIdempotent(self) -> None:
        """
        Remove a header and tolerate a second removal.

        Validates that middleware can strip headers unconditionally.
        """
        result = Response(headers={"X-A": "1"})
        result.removeHeader("X-A")
        result.removeHeader("X-A")
        self.assertFalse(result.hasHeader("x-a"))

    def testRawHeadersAreEncodedForTheTransport(self) -> None:
        """
        Expose every header value as latin-1 byte pairs.

        Validates the shape consumed by the ASGI response adapter.
        """
        result = Response(headers={"X-A": "1"})
        result.addHeader("x-a", "2")
        self.assertEqual(
            result.getRawHeaders(),
            [(b"x-a", b"1"), (b"x-a", b"2")],
        )

    def testStringHeadersFlattenMultipleValues(self) -> None:
        """
        Expose every header value as string pairs.

        Validates the shape consumed by the RSGI response adapter.
        """
        result = Response(headers={"X-A": "1"})
        result.addHeader("x-a", "2")
        self.assertEqual(result.getStringHeaders(), [("x-a", "1"), ("x-a", "2")])


class TestResponseCookies(TestCase):

    def testSetsACookieWithFrameworkDefaults(self) -> None:
        """
        Emit a cookie scoped to the root path with lax same-site.

        Validates the defaults applied when only a name and value are
        supplied.
        """
        result = Response()
        result.setCookie("theme", "dark")
        header = result.getHeader("set-cookie")[0]
        self.assertIn("theme=dark", header)
        self.assertIn("Path=/", header)
        self.assertIn("SameSite=lax", header)

    def testPercentEncodesTheCookieValue(self) -> None:
        """
        Percent-encode values carrying reserved characters.

        Validates that an e-mail address is not wrapped in double quotes
        by the standard library serializer.
        """
        result = Response()
        result.setCookie("user", "a@b.test")
        self.assertIn("user=a%40b.test", result.getHeader("set-cookie")[0])

    def testSetsTheMaxAgeAttribute(self) -> None:
        """
        Emit the ``Max-Age`` attribute when a lifetime is supplied.

        Validates the attribute browsers use to expire session cookies.
        """
        result = Response()
        result.setCookie("sid", "1", max_age=60)
        self.assertIn("Max-Age=60", result.getHeader("set-cookie")[0])

    def testNormalisesANaiveExpiryToUtc(self) -> None:
        """
        Treat a naive expiry datetime as UTC.

        Validates that a developer omitting the timezone does not shift
        the expiry by the machine offset.
        """
        result = Response()
        result.setCookie("sid", "1", expires=datetime(2026, 1, 2, 3, 4, 5))
        self.assertIn(
            "expires=Fri, 02 Jan 2026 03:04:05 GMT",
            result.getHeader("set-cookie")[0],
        )

    def testConvertsAnAwareExpiryToUtc(self) -> None:
        """
        Convert an aware expiry datetime into GMT.

        Validates that offsets are applied before the header is rendered.
        """
        result = Response()
        result.setCookie(
            "sid",
            "1",
            expires=datetime(
                2026, 1, 2, 5, 4, 5,
                tzinfo=timezone(timedelta(hours=2)),
            ),
        )
        self.assertIn(
            "expires=Fri, 02 Jan 2026 03:04:05 GMT",
            result.getHeader("set-cookie")[0],
        )

    def testAcceptsAPreformattedExpiry(self) -> None:
        """
        Emit a textual expiry value verbatim.

        Validates interoperability with callers that already formatted the
        date themselves.
        """
        result = Response()
        result.setCookie("sid", "1", expires="Wed, 21 Oct 2026 07:28:00 GMT")
        self.assertIn(
            "expires=Wed, 21 Oct 2026 07:28:00 GMT",
            result.getHeader("set-cookie")[0],
        )

    def testOmitsThePathWhenItIsEmpty(self) -> None:
        """
        Skip the ``Path`` attribute when no path is supplied.

        Validates that the cookie inherits the request path instead of
        being pinned to the root.
        """
        result = Response()
        result.setCookie("sid", "1", path=None)
        self.assertNotIn("Path=", result.getHeader("set-cookie")[0])

    def testSetsTheDomainAttribute(self) -> None:
        """
        Emit the ``Domain`` attribute when a domain is supplied.

        Validates cookies shared across subdomains.
        """
        result = Response()
        result.setCookie("sid", "1", domain="orionis.test")
        self.assertIn("Domain=orionis.test", result.getHeader("set-cookie")[0])

    def testRejectsAnUnknownSameSitePolicy(self) -> None:
        """
        Reject a same-site policy outside the specification.

        Validates that a typo cannot silently disable cross-site
        protection.
        """
        with self.assertRaises(ValueError):
            Response().setCookie("sid", "1", same_site="always")  # type: ignore[arg-type]

    def testRejectsSameSiteNoneWithoutSecure(self) -> None:
        """
        Reject ``SameSite=None`` on a non-secure cookie.

        Validates the browser requirement that would otherwise cause the
        cookie to be dropped silently.
        """
        with self.assertRaises(ValueError):
            Response().setCookie("sid", "1", same_site="none")

    def testAllowsSameSiteNoneOnSecureCookies(self) -> None:
        """
        Allow ``SameSite=None`` when the cookie is marked secure.

        Validates the configuration required by cross-site embeds.
        """
        result = Response()
        result.setCookie("sid", "1", same_site="none", secure=True)
        header = result.getHeader("set-cookie")[0]
        self.assertIn("SameSite=none", header)
        self.assertIn("Secure", header)

    def testOmitsSameSiteWhenDisabled(self) -> None:
        """
        Skip the ``SameSite`` attribute when the policy is ``None``.

        Validates the escape hatch for clients that reject the attribute.
        """
        result = Response()
        result.setCookie("sid", "1", same_site=None)
        self.assertNotIn("SameSite", result.getHeader("set-cookie")[0])

    def testMarksTheCookieHttpOnly(self) -> None:
        """
        Emit the ``HttpOnly`` attribute when requested.

        Validates the flag that hides session cookies from scripts.
        """
        result = Response()
        result.setCookie("sid", "1", http_only=True)
        self.assertIn("HttpOnly", result.getHeader("set-cookie")[0])

    def testMarksTheCookiePartitioned(self) -> None:
        """
        Emit the ``Partitioned`` attribute when requested.

        Validates support for cookies stored per top-level site.
        """
        result = Response()
        result.setCookie("sid", "1", partitioned=True)
        self.assertIn("Partitioned", result.getHeader("set-cookie")[0])

    def testDeleteCookieExpiresItInThePast(self) -> None:
        """
        Expire a cookie by rewriting it with a past date.

        Validates the only portable way of removing a stored cookie.
        """
        result = Response()
        result.deleteCookie("sid", domain="orionis.test")
        header = result.getHeader("set-cookie")[0]
        self.assertIn("Max-Age=0", header)
        self.assertIn("01 Jan 1970", header)
        self.assertIn("Domain=orionis.test", header)

    def testWithCookieReturnsTheSameResponse(self) -> None:
        """
        Return the response itself so cookies can be chained.

        Validates the fluent form used by controllers.
        """
        result = Response()
        self.assertIs(result.withCookie("sid", "1"), result)
        self.assertTrue(result.hasHeader("set-cookie"))

    def testWithCookiesAcceptsPlainValues(self) -> None:
        """
        Set several cookies from a mapping of plain values.

        Validates the shortest bulk form.
        """
        result = Response().withCookies({"a": "1", "b": "2"})
        self.assertEqual(len(result.getHeader("set-cookie")), 2)

    def testWithCookiesAcceptsPerCookieOptions(self) -> None:
        """
        Set a cookie from a mapping of keyword options.

        Validates that attributes such as ``http_only`` survive the bulk
        form.
        """
        result = Response().withCookies(
            {"sid": {"value": "1", "http_only": True}},
        )
        self.assertIn("HttpOnly", result.getHeader("set-cookie")[0])

    def testWithoutCookieExpiresAndChains(self) -> None:
        """
        Expire a cookie and return the response for chaining.

        Validates the fluent counterpart of ``deleteCookie``.
        """
        result = Response()
        self.assertIs(result.withoutCookie("sid"), result)
        self.assertIn("Max-Age=0", result.getHeader("set-cookie")[0])


class TestResponseFlash(TestCase):

    def testNothingIsQueuedByDefault(self) -> None:
        """
        Allocate no flash bag for a plain response.

        Validates that the vast majority of responses pay nothing for the
        flash feature.
        """
        self.assertIsNone(Response().getFlashData())

    def testWithFlashQueuesStatusMessages(self) -> None:
        """
        Queue status messages for the next request.

        Validates the bag consumed by the session middleware, including
        the reuse of an already allocated bag.
        """
        result = Response().withFlash("success", "Saved").withFlash("level", "info")
        self.assertEqual(
            result.getFlashData(),
            {"success": "Saved", "level": "info"},
        )

    def testWithInputStripsCredentials(self) -> None:
        """
        Queue the submitted payload without credential fields.

        Validates that repopulating a form never echoes a password back to
        the browser.
        """
        result = Response().withInput(
            {"email": "user@mail.test", _CREDENTIAL_FIELD: "hunter2"},
        )
        self.assertEqual(
            result.getFlashData()[OLD_INPUT_KEY],
            {"email": "user@mail.test"},
        )

    def testWithErrorsNormalisesTheMapping(self) -> None:
        """
        Queue field errors as lists of messages.

        Validates the shape read back by the ``errors`` template global.
        """
        result = Response().withErrors({"email": "Invalid."})
        self.assertEqual(
            result.getFlashData()[ERRORS_KEY],
            {"email": ["Invalid."]},
        )

    def testFlashHelpersShareASingleBag(self) -> None:
        """
        Merge every flash helper into one payload.

        Validates that queueing input after errors does not discard the
        previously queued bag.
        """
        result = (
            Response()
            .withErrors({"email": "Invalid."})
            .withInput({"email": "x"})
            .withFlash("status", "failed")
        )
        self.assertEqual(
            sorted(result.getFlashData()),
            sorted([ERRORS_KEY, OLD_INPUT_KEY, "status"]),
        )

    def testFluentHelpersReturnTheSameResponse(self) -> None:
        """
        Return the response itself from every flash helper.

        Validates that the helpers can be chained in a single return
        statement.
        """
        result = Response()
        self.assertIs(result.withFlash("a"), result)
        self.assertIs(result.withInput({}), result)
        self.assertIs(result.withErrors({}), result)


class TestResponseAccessors(TestCase):

    def testExposesTheStatusCodeAndMediaType(self) -> None:
        """
        Expose the status code and media type given at construction time.

        Validates the accessors read by the transport adapters.
        """
        result = Response(status_code=201, media_type="text/csv")
        self.assertEqual(result.getStatusCode(), 201)
        self.assertEqual(result.getMediaType(), "text/csv")

    def testReportsTheAbsenceOfAStream(self) -> None:
        """
        Report a buffered response as having no stream.

        Validates the branch that lets the adapter send a single frame.
        """
        result = Response(content="body")
        self.assertFalse(result.hasStream())
        self.assertIsNone(result.getStream())

    async def testExposesTheAttachedStream(self) -> None:
        """
        Expose the asynchronous iterator attached to the response.

        Validates that the adapter can forward the chunks unchanged.
        """
        result = Response(content=_async_chunks())
        self.assertEqual(await _drain(result.getStream()), [b"first", b"second"])

    async def testRunBackgroundIsANoOpWithoutATask(self) -> None:
        """
        Do nothing when no background task is attached.

        Validates that every response can be finalised through the same
        code path.
        """
        self.assertIsNone(await Response().runBackground())

    async def testRunBackgroundExecutesTheTask(self) -> None:
        """
        Execute the attached background task once.

        Validates the hook used to run work after the response is sent.
        """
        executed: list[str] = []
        result = Response(background=BackgroundTask(executed.append, "done"))
        await result.runBackground()
        self.assertEqual(executed, ["done"])


class TestHtmlResponse(TestCase):

    def testAdvertisesTheHtmlContentType(self) -> None:
        """
        Set the HTML content type when none is supplied.

        Validates the default applied to every rendered view.
        """
        result = HTMLResponse("<h1>hi</h1>")
        self.assertEqual(
            result.getHeader("content-type"),
            ["text/html; charset=utf-8"],
        )
        self.assertEqual(result.getMediaType(), "text/html")

    def testKeepsAnExplicitContentType(self) -> None:
        """
        Preserve a content type supplied by the caller.

        Validates support for alternative charsets or XHTML variants.
        """
        result = HTMLResponse(
            "<h1>hi</h1>",
            headers={"content-type": "text/html; charset=latin-1"},
        )
        self.assertEqual(
            result.getHeader("content-type"),
            ["text/html; charset=latin-1"],
        )

    def testDefaultsToAnEmptyOkBody(self) -> None:
        """
        Build an empty ``200`` response when no content is supplied.

        Validates that the class is usable as a placeholder.
        """
        result = HTMLResponse()
        self.assertEqual(result.getBody(), b"")
        self.assertEqual(result.getStatusCode(), 200)


class TestPlainTextResponse(TestCase):

    def testAdvertisesThePlainTextContentType(self) -> None:
        """
        Set the plain-text content type when none is supplied.

        Validates the default applied to text endpoints.
        """
        result = PlainTextResponse("ok")
        self.assertEqual(
            result.getHeader("content-type"),
            ["text/plain; charset=utf-8"],
        )
        self.assertEqual(result.getMediaType(), "text/plain")

    def testKeepsAnExplicitContentType(self) -> None:
        """
        Preserve a content type supplied by the caller.

        Validates support for formats such as CSV served as text.
        """
        result = PlainTextResponse("a,b", headers={"content-type": "text/csv"})
        self.assertEqual(result.getHeader("content-type"), ["text/csv"])


class TestJsonResponse(TestCase):

    def testSerialisesThroughTheFastPath(self) -> None:
        """
        Serialise the payload with the compact encoder by default.

        Validates the branch taken by virtually every API response.
        """
        result = JSONResponse({"a": 1, "b": [1, 2]})
        self.assertEqual(result.getBody(), b'{"a":1,"b":[1,2]}')

    def testAdvertisesTheJsonContentType(self) -> None:
        """
        Set the JSON content type when none is supplied.

        Validates the header clients rely on to decode the payload.
        """
        self.assertEqual(
            JSONResponse({}).getHeader("content-type"),
            ["application/json; charset=utf-8"],
        )

    def testKeepsAnExplicitContentType(self) -> None:
        """
        Preserve a content type supplied by the caller.

        Validates support for JSON API media types.
        """
        result = JSONResponse(
            {},
            headers={"content-type": "application/vnd.api+json"},
        )
        self.assertEqual(
            result.getHeader("content-type"),
            ["application/vnd.api+json"],
        )

    def testPrettyPrintsWhenIndentIsRequested(self) -> None:
        """
        Indent the payload when an indentation level is supplied.

        Validates the slow path backed by the standard library encoder.
        """
        result = JSONResponse({"a": 1}, indent=4)
        self.assertEqual(result.getBody(), b'{\n    "a": 1\n}')

    def testEscapesNonAsciiWhenRequested(self) -> None:
        """
        Escape non-ASCII characters when asked to.

        Validates the compact separators applied on the escaping path.
        """
        result = JSONResponse({"name": "ñ"}, ensure_ascii=True)
        self.assertEqual(result.getBody(), b'{"name":"\\u00f1"}')

    def testHonoursCustomSeparators(self) -> None:
        """
        Use the caller-supplied item and key separators.

        Validates interoperability with clients expecting spaced output.
        """
        result = JSONResponse({"a": 1, "b": 2}, separators=(", ", ": "))
        self.assertEqual(result.getBody(), b'{"a": 1, "b": 2}')

    def testFastPathReportsUnserialisableContent(self) -> None:
        """
        Raise a type error for content the encoder cannot handle.

        Validates that a handler returning an opaque object fails loudly.
        """
        with self.assertRaises(TypeError):
            JSONResponse({"value": _Opaque()})

    def testSlowPathReportsUnserialisableContent(self) -> None:
        """
        Raise a type error on the pretty-printing path as well.

        Validates that formatting options do not swallow encoding errors.
        """
        with self.assertRaises(TypeError):
            JSONResponse({"value": _Opaque()}, indent=2)

    def testUsesTheCallerSuppliedEncoder(self) -> None:
        """
        Delegate unsupported types to the caller-supplied encoder.

        Validates the hook that lets applications serialise their own
        value objects.
        """
        result = JSONResponse(
            {"value": _Opaque()},
            default=lambda _value: "opaque",
        )
        self.assertEqual(result.getBody(), b'{"value":"opaque"}')


class TestJsonResponseDefaultEncoder(TestCase):

    def testEncodesTemporalValuesAsIsoStrings(self) -> None:
        """
        Render datetimes, dates and times in ISO 8601.

        Validates the format consumed by JavaScript clients.
        """
        encode = JSONResponse._defaultEncoder
        self.assertEqual(
            encode(datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)),
            "2026-01-02T03:04:05+00:00",
        )
        self.assertEqual(encode(date(2026, 1, 2)), "2026-01-02")
        self.assertEqual(encode(time(3, 4, 5)), "03:04:05")

    def testEncodesDecimalsAsStrings(self) -> None:
        """
        Render decimals as text to preserve precision.

        Validates that monetary amounts never lose digits to a float.
        """
        self.assertEqual(JSONResponse._defaultEncoder(Decimal("1.10")), "1.10")

    def testEncodesUuidsAsStrings(self) -> None:
        """
        Render identifiers in their canonical textual form.

        Validates the representation expected by API consumers.
        """
        identifier = UUID("12345678-1234-5678-1234-567812345678")
        self.assertEqual(
            JSONResponse._defaultEncoder(identifier),
            "12345678-1234-5678-1234-567812345678",
        )

    def testEncodesEnumerationsByValue(self) -> None:
        """
        Render enumeration members using their value.

        Validates that domain enumerations serialise as plain scalars.
        """
        self.assertEqual(JSONResponse._defaultEncoder(_Colour.RED), "red")

    def testEncodesSetsAsLists(self) -> None:
        """
        Render sets and frozen sets as JSON arrays.

        Validates that unordered collections are still serialisable.
        """
        encode = JSONResponse._defaultEncoder
        self.assertEqual(encode({"only"}), ["only"])
        self.assertEqual(encode(frozenset({"only"})), ["only"])

    def testRejectsUnknownTypes(self) -> None:
        """
        Raise a type error naming the offending type.

        Validates the diagnostic returned for unsupported payloads.
        """
        with self.assertRaises(TypeError) as captured:
            JSONResponse._defaultEncoder(_Opaque())
        self.assertIn("_Opaque", str(captured.exception))


class TestRedirectResponse(TestCase):

    def testRejectsANonStringUrl(self) -> None:
        """
        Reject a redirect target that is not a string.

        Validates that a path object cannot reach the location header
        unconverted.
        """
        with self.assertRaises(TypeError):
            RedirectResponse(url=Path("/login"))  # type: ignore[arg-type]

    def testRejectsANonRedirectStatusCode(self) -> None:
        """
        Reject a status code outside the ``3xx`` range.

        Validates that only real redirects can be built with this class.
        """
        with self.assertRaises(ValueError):
            RedirectResponse(url="/login", status_code=200)

    def testSetsTheLocationHeader(self) -> None:
        """
        Expose the target in the ``Location`` header.

        Validates the header browsers follow.
        """
        result = RedirectResponse("/dashboard")
        self.assertEqual(result.getHeader("location"), ["/dashboard"])
        self.assertEqual(result.getStatusCode(), 302)

    def testProvidesAHumanReadableBody(self) -> None:
        """
        Render a textual body describing the redirect.

        Validates the fallback shown by clients that do not follow the
        header automatically.
        """
        self.assertEqual(
            RedirectResponse("/dashboard").getBody(),
            b"Redirecting to /dashboard",
        )

    def testAdvertisesThePlainTextContentType(self) -> None:
        """
        Set the plain-text content type when none is supplied.

        Validates the default applied to the descriptive body.
        """
        self.assertEqual(
            RedirectResponse("/x").getHeader("content-type"),
            ["text/plain; charset=utf-8"],
        )

    def testKeepsAnExplicitContentType(self) -> None:
        """
        Preserve a content type supplied by the caller.

        Validates that an HTML redirect body can be served instead.
        """
        result = RedirectResponse(
            "/x",
            headers={"content-type": "text/html"},
        )
        self.assertEqual(result.getHeader("content-type"), ["text/html"])


class TestStreamingResponse(TestCase):

    async def testAcceptsAnAsynchronousIterable(self) -> None:
        """
        Stream the chunks produced by an asynchronous iterable.

        Validates the native path used by generators.
        """
        result = StreamingResponse(_async_chunks())
        self.assertEqual(await _drain(result.getStream()), [b"first", b"second"])

    async def testAdaptsASynchronousIterable(self) -> None:
        """
        Stream the chunks produced by a synchronous iterable.

        Validates that ordinary lists and generators are usable without
        an explicit adapter.
        """
        result = StreamingResponse([b"a", bytearray(b"b"), memoryview(b"c")])
        self.assertEqual(await _drain(result.getStream()), [b"a", b"b", b"c"])

    async def testRejectsChunksThatAreNotBytes(self) -> None:
        """
        Reject a chunk that cannot be written to the socket.

        Validates that textual chunks fail at the first iteration instead
        of corrupting the response.
        """
        result = StreamingResponse(["text"])  # type: ignore[list-item]
        with self.assertRaises(TypeError):
            await _drain(result.getStream())

    def testRejectsContentThatIsNotIterable(self) -> None:
        """
        Reject content that can be neither iterated nor awaited.

        Validates the guard protecting the transport adapters.
        """
        with self.assertRaises(TypeError):
            StreamingResponse(object())  # type: ignore[arg-type]

    def testNeverBuffersABody(self) -> None:
        """
        Leave the buffered body empty for streamed responses.

        Validates that the adapter selects the streaming send path.
        """
        result = StreamingResponse([b"a"])
        self.assertIsNone(result.getBody())
        self.assertTrue(result.hasStream())

    def testAppendsTheCharsetToTextualMediaTypes(self) -> None:
        """
        Append the charset to textual media types.

        Validates that streamed text is decoded correctly by the client.
        """
        result = StreamingResponse([b"a"], media_type="text/event-stream")
        self.assertEqual(
            result.getHeader("content-type"),
            ["text/event-stream; charset=utf-8"],
        )

    def testKeepsBinaryMediaTypesVerbatim(self) -> None:
        """
        Emit binary media types without a charset.

        Validates that downloads are not advertised as text.
        """
        result = StreamingResponse([b"a"], media_type="application/octet-stream")
        self.assertEqual(
            result.getHeader("content-type"),
            ["application/octet-stream"],
        )

    def testOmitsTheContentTypeWhenNoMediaTypeIsGiven(self) -> None:
        """
        Leave the content type unset when no media type is supplied.

        Validates that the caller keeps full control over negotiation.
        """
        self.assertFalse(StreamingResponse([b"a"]).hasHeader("content-type"))

    def testKeepsAnExplicitContentType(self) -> None:
        """
        Preserve a content type supplied by the caller.

        Validates that the media type does not overwrite an explicit
        header.
        """
        result = StreamingResponse(
            [b"a"],
            media_type="text/plain",
            headers={"content-type": "text/csv"},
        )
        self.assertEqual(result.getHeader("content-type"), ["text/csv"])


class TestFileResponse(TestCase):

    def setUp(self) -> None:
        """
        Create a temporary file served by the response under test.

        Validates the class against real filesystem metadata instead of
        stubbed values.
        """
        self._tmp = TemporaryDirectory()
        self._root = Path(self._tmp.name)
        self._file = self._root / "report.txt"
        self._file.write_bytes(b"0123456789")

    def tearDown(self) -> None:
        """
        Remove the temporary directory after the test.

        Validates that the suite leaves no artefacts behind.
        """
        self._tmp.cleanup()

    def testRejectsAMissingFile(self) -> None:
        """
        Reject a path that does not exist.

        Validates that a broken download fails at construction time.
        """
        with self.assertRaises(FileNotFoundError):
            FileResponse(self._root / "missing.txt")

    def testRejectsADirectory(self) -> None:
        """
        Reject a path that points at a directory.

        Validates that the response never tries to stream a folder.
        """
        with self.assertRaises(ValueError):
            FileResponse(self._root)

    def testGuessesTheMediaTypeFromTheExtension(self) -> None:
        """
        Infer the media type from the file extension.

        Validates the convenience relied upon by static file handlers.
        """
        result = FileResponse(self._file)
        self.assertEqual(result.getMediaType(), "text/plain")

    def testFallsBackToABinaryMediaType(self) -> None:
        """
        Fall back to a binary media type for unknown extensions.

        Validates that an unrecognised file is still downloadable.
        """
        unknown = self._root / "archive.orionis"
        unknown.write_bytes(b"x")
        self.assertEqual(
            FileResponse(unknown).getMediaType(),
            "application/octet-stream",
        )

    def testHonoursAnExplicitMediaType(self) -> None:
        """
        Use the media type supplied by the caller.

        Validates that generated files can override the guess.
        """
        result = FileResponse(self._file, media_type="application/pdf")
        self.assertEqual(result.getMediaType(), "application/pdf")

    def testAdvertisesTheFileSize(self) -> None:
        """
        Expose the file size through the content-length header.

        Validates that clients can display download progress.
        """
        result = FileResponse(str(self._file))
        self.assertEqual(result.getFileSize(), 10)
        self.assertEqual(result.getHeader("content-length"), ["10"])

    def testExposesTheServedPath(self) -> None:
        """
        Expose the resolved path of the served file.

        Validates the accessor used to derive a default attachment name.
        """
        self.assertEqual(FileResponse(self._file).getPath(), self._file)

    def testSetsTheAttachmentHeaderWhenNamed(self) -> None:
        """
        Advertise the attachment name when a filename is supplied.

        Validates the header instructing the browser to download.
        """
        result = FileResponse(self._file, filename="invoice.txt")
        self.assertEqual(
            result.getHeader("content-disposition"),
            ['attachment; filename="invoice.txt"'],
        )

    def testOmitsTheAttachmentHeaderByDefault(self) -> None:
        """
        Leave the disposition unset when no filename is supplied.

        Validates that inline rendering stays the default.
        """
        self.assertFalse(
            FileResponse(self._file).hasHeader("content-disposition"),
        )

    async def testStreamsTheFileInChunks(self) -> None:
        """
        Stream the file contents in fixed-size chunks.

        Validates that large downloads never load the whole file into
        memory.
        """
        result = FileResponse(self._file, chunk_size=4)
        self.assertEqual(
            await _drain(result.getStream()),
            [b"0123", b"4567", b"89"],
        )

    async def testStreamsAnEmptyFileWithoutChunks(self) -> None:
        """
        Produce no chunk at all for an empty file.

        Validates the loop termination condition of the file iterator.
        """
        empty = self._root / "empty.txt"
        empty.write_bytes(b"")
        result = FileResponse(empty)
        self.assertEqual(await _drain(result.getStream()), [])

    async def testStreamingRunsOnTheEventLoop(self) -> None:
        """
        Read the file through the running event loop executor.

        Validates that blocking reads never stall the loop.
        """
        result = FileResponse(self._file)
        loop = asyncio.get_running_loop()
        self.assertTrue(loop.is_running())
        self.assertEqual(await _drain(result.getStream()), [b"0123456789"])
