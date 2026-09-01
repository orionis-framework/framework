from orionis.http.layer.contracts.middleware import IBaseMiddleware
from orionis.http.middleware import BaseMiddleware, NextCallable
from orionis.http.responses import Response
from orionis.test import TestCase


class _BareMiddleware(BaseMiddleware):
    """Middleware that forgets to override the request hook."""

    __slots__ = ()


class _PassThroughMiddleware(BaseMiddleware):
    """Middleware that simply advances the pipeline."""

    __slots__ = ()

    async def handle(
        self,
        _request: object,
        call_next: NextCallable,
    ) -> Response:
        """
        Advance to the next layer and tag the response.

        Parameters
        ----------
        _request : object
            Incoming HTTP request.
        call_next : NextCallable
            Pipeline continuation.

        Returns
        -------
        Response
            Response produced downstream, carrying a marker header.
        """
        response = await call_next()
        response.setHeader("x-visited", "1")
        return response


async def terminal() -> Response:
    """
    Return the response produced at the end of the pipeline.

    Returns
    -------
    Response
        Response carrying a fixed marker body.
    """
    return Response(content="handler")


class TestBaseMiddlewareContract(TestCase):

    def testImplementsTheMiddlewareContract(self) -> None:
        """
        Derive the base class from the middleware contract.

        Validates that every middleware is accepted wherever the kernel
        expects the interface.
        """
        self.assertTrue(issubclass(BaseMiddleware, IBaseMiddleware))

    def testDoesNotExposeAnInstanceDictionary(self) -> None:
        """
        Keep middleware instances free of a per-instance dictionary.

        Validates the slot layout shared by the whole middleware stack,
        which is instantiated once per application boot.
        """
        self.assertFalse(hasattr(_PassThroughMiddleware(), "__dict__"))


class TestBaseMiddlewareHandle(TestCase):

    async def testRejectsASubclassThatDoesNotOverrideHandle(self) -> None:
        """
        Refuse to serve a middleware without a request hook.

        Validates that an incomplete middleware fails loudly instead of
        silently dropping the request.
        """
        with self.assertRaises(NotImplementedError):
            await _BareMiddleware().handle(None, terminal)

    async def testNamesTheOffendingSubclass(self) -> None:
        """
        Name the offending subclass in the diagnostic.

        Validates that the message points straight at the class to fix.
        """
        with self.assertRaises(NotImplementedError) as captured:
            await _BareMiddleware().handle(None, terminal)
        self.assertIn("_BareMiddleware", str(captured.exception))

    async def testSubclassesCanAdvanceThePipeline(self) -> None:
        """
        Let a concrete middleware run the rest of the pipeline.

        Validates the contract every application middleware relies on.
        """
        response = await _PassThroughMiddleware().handle(None, terminal)
        self.assertEqual(response.getBody(), b"handler")
        self.assertEqual(response.getHeader("x-visited"), ["1"])
