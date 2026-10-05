import socket
from threading import get_ident
from typing import Annotated
from orionis.schemas.rules.active_url import ActiveUrl
from orionis.schemas.schema import Schema
from orionis.schemas.validator import Schema as Validator
from orionis.test import TestCase

class _UrlPayload(Schema):
    """Declare a native DNS rule for asynchronous schema validation."""

    url: Annotated[str, ActiveUrl()]

class _Resolver:
    """Record resolver threads without consulting an external DNS server."""

    __slots__ = ("calls", "failure")

    def __init__(self) -> None:
        """Prepare empty resolver observations.

        Returns
        -------
        None
            Queries will succeed unless a test supplies a failure.
        """
        self.calls: list[tuple[int, str]] = []
        self.failure: OSError | UnicodeError | None = None

    def resolve(self, host: str, *_args: object, **_kwargs: object) -> list[tuple]:
        """Record the calling thread and provide a deterministic DNS result.

        Parameters
        ----------
        host : str
            Hostname submitted to the system resolver.
        *_args : object
            Positional resolver options.
        **_kwargs : object
            Keyword resolver options.

        Returns
        -------
        list[tuple]
            Empty successful resolver result.

        Raises
        ------
        OSError
            If the test supplied a resolver failure.
        UnicodeError
            If the test supplied an invalid hostname encoding failure.
        """
        self.calls.append((get_ident(), host))
        if self.failure is not None:
            raise self.failure
        return []

class TestActiveUrlAsync(TestCase):
    """Verify DNS thread ownership and rejection semantics without network I/O."""

    def setUp(self) -> None:
        """Install a recording system resolver for this test.

        Returns
        -------
        None
            DNS calls are captured by a test-owned double.
        """
        self._original = socket.getaddrinfo
        self._resolver = _Resolver()
        socket.getaddrinfo = self._resolver.resolve

    def tearDown(self) -> None:
        """Restore the system resolver after all awaited work completes.

        Returns
        -------
        None
            Subsequent tests use the original resolver.
        """
        socket.getaddrinfo = self._original

    async def testValidationResolvesOutsideTheEventLoopThread(self) -> None:
        """Move DNS resolution to the loop's worker executor.

        Returns
        -------
        None
            The URL is accepted and the resolver runs in another thread.
        """
        thread_id = get_ident()
        payload = await Validator.validateAsync(
            {"url": "https://service.example/path"}, _UrlPayload,
        )
        self.assertEqual(payload.url, "https://service.example/path")
        self.assertEqual(len(self._resolver.calls), 1)
        resolved_thread, host = self._resolver.calls[0]
        self.assertNotEqual(resolved_thread, thread_id)
        self.assertEqual(host, "service.example")

    async def testInvalidUrlsAndNonStringsNeverReachDns(self) -> None:
        """Preserve type-layer delegation and invalid-URL rejection.

        Returns
        -------
        None
            Inputs without a usable hostname trigger no resolver calls.
        """
        rule = ActiveUrl()
        for value in (None, 42):
            self.assertTrue(await rule.enforceAsync("url", value, None))
        for value in ("", "relative/path", "https://["):
            self.assertFalse(await rule.enforceAsync("url", value, None))
        self.assertEqual(self._resolver.calls, [])

    async def testResolverFailuresProduceValidationFailures(self) -> None:
        """Translate expected resolver failures into field validation errors.

        Returns
        -------
        None
            DNS and hostname encoding failures retain the active_url rule code.
        """
        message = "Resolver rejected the hostname"
        for failure in (socket.gaierror(message), UnicodeError(message)):
            self._resolver.failure = failure
            result = await ActiveUrl().validateAsync(
                "url", "https://service.example", None,
            )
            self.assertIsNotNone(result)
            self.assertEqual(result.rule, "active_url")
