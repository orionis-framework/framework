from typing import Any
from orionis.http.response import HTMLResponse
from orionis.test import TestCase
from orionis.view import pending as pending_module
from orionis.view.exceptions import (
    ViewRenderException,
    ViewTemplateNotFoundException,
)
from orionis.view.pending import PendingView

# Neutral placeholder used wherever a credential-like field is required.
_CREDENTIAL: str = "not-a-real-value"

# Failure messages hoisted out of the raise statements (EM101).
_ENGINE_FAILURE: str = "engine exploded"
_INVALID_PAYLOAD: str = "payload is invalid"
_MISSING_TEMPLATE: str = "template not found"
_NO_SESSION: str = "no active session"
_QUALNAME_FAILURE: str = "_global_csrf_field.<locals>.csrf_field is broken"

class _StubEngine:
    """View engine double recording calls and returning canned output."""

    __slots__ = ("calls", "error", "html")

    def __init__(
        self,
        html: str = "<p>ok</p>",
        error: Exception | None = None,
    ) -> None:
        self.html: str = html
        self.error: Exception | None = error
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def render(self, template: str, context: dict[str, Any]) -> str:
        """Return the canned HTML or raise the configured error."""
        self.calls.append((template, context))
        if self.error is not None:
            raise self.error
        return self.html

class _StubSession:
    """Session double capturing every flash write it receives."""

    __slots__ = ("errors", "inputs", "messages")

    def __init__(self) -> None:
        self.messages: dict[str, Any] = {}
        self.inputs: dict[str, Any] = {}
        self.errors: dict[str, Any] = {}

    def flash(self, key: str, value: object) -> None:
        """Store a single flash message."""
        self.messages[key] = value

    def flashInput(self, values: dict[str, Any]) -> None:
        """Merge old-input values into the captured bag."""
        self.inputs.update(values)

    def flashErrors(self, errors: dict[str, Any]) -> None:
        """Merge validation errors into the captured bag."""
        self.errors.update(errors)

class _StubSessionFacade:
    """Session facade double returning a session or failing resolution."""

    __slots__ = ("failure", "resolved", "session")

    def __init__(
        self,
        session: _StubSession | None = None,
        failure: Exception | None = None,
    ) -> None:
        self.session: _StubSession | None = session
        self.failure: Exception | None = failure
        self.resolved: int = 0

    async def resolve(self) -> _StubSession | None:
        """Return the stubbed session or raise the configured failure."""
        self.resolved += 1
        if self.failure is not None:
            raise self.failure
        return self.session

class _StubValidationError(Exception):
    """Validation error exposing an ``errors`` mapping like the real one."""

    def __init__(self, errors: dict[str, list[str]]) -> None:
        super().__init__(_INVALID_PAYLOAD)
        self.errors: dict[str, list[str]] = errors

class TestPendingViewConstruction(TestCase):

    def testConstructionDoesNotRenderEagerly(self) -> None:
        """
        Defer all rendering work until the view is awaited.

        Validates that building a PendingView never touches the engine,
        keeping ``make()`` free of I/O.
        """
        engine = _StubEngine()
        PendingView(engine, "users.index", {})
        self.assertEqual(engine.calls, [])

    def testConstructionStoresRenderingIntent(self) -> None:
        """
        Store the engine, template and context supplied by the factory.

        Validates that the pending view keeps the exact rendering intent
        it was built with.
        """
        engine = _StubEngine()
        context = {"name": "World"}
        view = PendingView(engine, "users.index", context)
        self.assertIs(view._engine, engine)
        self.assertEqual(view._template, "users.index")
        self.assertIs(view._context, context)

    def testConstructionLeavesQueuesEmpty(self) -> None:
        """
        Leave the mutation and flash queues unallocated on construction.

        Validates the lazy-allocation strategy: no dictionary or list is
        created until a mutator is actually chained.
        """
        view = PendingView(_StubEngine(), "users.index", {})
        self.assertIsNone(view._mutations)
        self.assertIsNone(view._flash)

class TestPendingViewFlashMutators(TestCase):

    def _make(self) -> PendingView:
        """Build a pending view backed by a stub engine."""
        return PendingView(_StubEngine(), "users.index", {})

    def testWithFlashReturnsSameInstance(self) -> None:
        """
        Return the same pending view from withFlash for fluent chaining.

        Validates that the mutator never clones the pending view so calls
        can be chained on a single object.
        """
        view = self._make()
        self.assertIs(view.withFlash("status", "saved"), view)

    def testWithFlashQueuesValue(self) -> None:
        """
        Queue the flash key and value without touching the session.

        Validates that the value is buffered locally until the view is
        rendered.
        """
        view = self._make()
        view.withFlash("status", "saved")
        self.assertEqual(view._flash, {"status": "saved"})

    def testWithFlashDefaultsValueToNone(self) -> None:
        """
        Queue a None value when no explicit value is supplied.

        Validates the optional second parameter of withFlash.
        """
        view = self._make()
        view.withFlash("notified")
        self.assertEqual(view._flash, {"notified": None})

    def testWithFlashAccumulatesKeys(self) -> None:
        """
        Accumulate several keys inside a single flash payload.

        Validates that repeated calls extend the queue instead of
        replacing previously queued entries.
        """
        view = self._make()
        view.withFlash("status", "saved").withFlash("level", "info")
        self.assertEqual(view._flash, {"status": "saved", "level": "info"})

    def testWithInputReturnsSameInstance(self) -> None:
        """
        Return the same pending view from withInput for fluent chaining.

        Validates that the mutator keeps the chain anchored on one object.
        """
        view = self._make()
        self.assertIs(view.withInput({"email": "user@example.com"}), view)

    def testWithInputStripsCredentialFields(self) -> None:
        """
        Drop credential-like fields from the flashed form payload.

        Validates that passwords are never written to the session when a
        form is repopulated.
        """
        view = self._make()
        view.withInput({"email": "user@example.com", "password": _CREDENTIAL})
        self.assertEqual(
            view._flash,
            {"_old_input": {"email": "user@example.com"}},
        )

    def testWithInputMergesRepeatedCalls(self) -> None:
        """
        Merge repeated withInput calls into a single old-input bag.

        Validates that the reserved bag is updated rather than replaced.
        """
        view = self._make()
        view.withInput({"email": "user@example.com"}).withInput({"age": 30})
        self.assertEqual(
            view._flash["_old_input"],
            {"email": "user@example.com", "age": 30},
        )

    def testWithErrorsReturnsSameInstance(self) -> None:
        """
        Return the same pending view from withErrors for fluent chaining.

        Validates that the mutator keeps the chain anchored on one object.
        """
        view = self._make()
        self.assertIs(view.withErrors({"email": "invalid"}), view)

    def testWithErrorsNormalisesSingleMessages(self) -> None:
        """
        Normalise a single error message into a list of messages.

        Validates that the errors bag always stores lists so templates
        can iterate them uniformly.
        """
        view = self._make()
        view.withErrors({"email": "invalid"})
        self.assertEqual(view._flash, {"_errors": {"email": ["invalid"]}})

    def testWithErrorsAcceptsValidationException(self) -> None:
        """
        Accept an exception exposing an errors mapping.

        Validates the duck-typed contract used by validation exceptions
        raised by the schemas package.
        """
        view = self._make()
        view.withErrors(_StubValidationError({"email": ["invalid"]}))
        self.assertEqual(view._flash, {"_errors": {"email": ["invalid"]}})

    def testWithErrorsMergesRepeatedCalls(self) -> None:
        """
        Merge repeated withErrors calls into a single errors bag.

        Validates that the reserved bag accumulates fields instead of
        overwriting the previous payload.
        """
        view = self._make()
        view.withErrors({"email": "invalid"}).withErrors({"name": "required"})
        self.assertEqual(
            view._flash["_errors"],
            {"email": ["invalid"], "name": ["required"]},
        )

    def testMutatorsShareOneFlashPayload(self) -> None:
        """
        Share a single flash payload across every flash mutator.

        Validates that messages, old input and errors coexist in the same
        queued payload.
        """
        view = self._make()
        view.withFlash("status", "failed")
        view.withInput({"email": "user@example.com"})
        view.withErrors({"email": "invalid"})
        self.assertEqual(
            sorted(view._flash),
            ["_errors", "_old_input", "status"],
        )

class TestPendingViewAttributeQueue(TestCase):

    def _make(self) -> PendingView:
        """Build a pending view backed by a stub engine."""
        return PendingView(_StubEngine(), "users.index", {})

    def testUnknownAttributeRaisesAttributeError(self) -> None:
        """
        Raise AttributeError for names absent from HTMLResponse.

        Validates that the proxy never silently swallows typos in
        chained response mutators.
        """
        view = self._make()
        with self.assertRaises(AttributeError):
            view.doesNotExist  # noqa: B018

    def testNonCallableAttributeRaisesAttributeError(self) -> None:
        """
        Raise AttributeError for non-callable HTMLResponse attributes.

        Validates that only methods can be queued for replay, never
        plain class attributes.
        """
        view = self._make()
        with self.assertRaises(AttributeError):
            view._CONTENT_TYPE  # noqa: B018

    def testQueuedCallReturnsSameInstance(self) -> None:
        """
        Return the same pending view from a queued response call.

        Validates that proxied response methods remain chainable.
        """
        view = self._make()
        self.assertIs(view.addHeader("X-Test", "1"), view)

    def testQueuedCallRecordsNameArgsAndKwargs(self) -> None:
        """
        Record the name, positional and keyword arguments of the call.

        Validates that the queued invocation carries everything needed to
        replay it on the rendered response.
        """
        view = self._make()
        view.withCookie("session", value="abc")
        self.assertEqual(
            view._mutations,
            [("withCookie", ("session",), {"value": "abc"})],
        )

    def testQueuedCallsPreserveOrder(self) -> None:
        """
        Preserve the order in which response calls were chained.

        Validates that replay order matches the call order written by the
        developer.
        """
        view = self._make()
        view.addHeader("X-Order", "first").addHeader("X-Order", "second")
        recorded = [name for name, _, _ in view._mutations]
        self.assertEqual(recorded, ["addHeader", "addHeader"])

class TestPendingViewRender(TestCase):

    def _make(
        self,
        html: str = "<p>ok</p>",
        error: Exception | None = None,
    ) -> tuple[PendingView, _StubEngine]:
        """Build a pending view together with its stub engine."""
        engine = _StubEngine(html=html, error=error)
        return PendingView(engine, "users.index", {"name": "World"}), engine

    async def testRenderReturnsHtmlResponse(self) -> None:
        """
        Return an HTMLResponse once the template has been rendered.

        Validates that the pending view materialises a framework-native
        response rather than a raw string.
        """
        view, _ = self._make()
        self.assertIsInstance(await view.render(), HTMLResponse)

    async def testAwaitRendersTheView(self) -> None:
        """
        Render the template when the pending view is awaited.

        Validates that __await__ delegates to render so controllers can
        simply await the value returned by the factory.
        """
        view, _ = self._make(html="<p>awaited</p>")
        response = await view
        self.assertEqual(response.getBody(), b"<p>awaited</p>")

    async def testRenderForwardsTemplateAndContext(self) -> None:
        """
        Forward the template name and context to the engine untouched.

        Validates that no transformation is applied to the rendering
        intent before it reaches the engine.
        """
        view, engine = self._make()
        await view.render()
        self.assertEqual(engine.calls, [("users.index", {"name": "World"})])

    async def testRenderSetsServerSideRenderHeader(self) -> None:
        """
        Mark the response with the X-Orionis-Render header.

        Validates that server-rendered responses are identifiable by
        clients and middleware.
        """
        view, _ = self._make()
        response = await view.render()
        self.assertEqual(response.getHeader("x-orionis-render"), ["SSR"])

    async def testRenderAppliesQueuedMutationsInOrder(self) -> None:
        """
        Replay every queued response call in the original order.

        Validates that chained mutators reach the real response exactly
        as they were written.
        """
        view, _ = self._make()
        view.addHeader("X-Order", "first").addHeader("X-Order", "second")
        response = await view.render()
        self.assertEqual(
            response.getHeader("x-order"),
            ["first", "second"],
        )

    async def testRenderWithoutMutationsSucceeds(self) -> None:
        """
        Render successfully when no response mutator was chained.

        Validates the fast path where the mutation queue stays empty.
        """
        view, _ = self._make(html="<p>plain</p>")
        response = await view.render()
        self.assertEqual(response.getBody(), b"<p>plain</p>")

    async def testRenderPropagatesTemplateNotFound(self) -> None:
        """
        Propagate ViewTemplateNotFoundException unchanged.

        Validates that a missing template keeps its own exception type
        instead of being wrapped as a render failure.
        """
        view, _ = self._make(
            error=ViewTemplateNotFoundException(_MISSING_TEMPLATE),
        )
        with self.assertRaises(ViewTemplateNotFoundException):
            await view.render()

    async def testRenderWrapsUnexpectedErrors(self) -> None:
        """
        Wrap any unexpected engine failure in ViewRenderException.

        Validates that the view layer exposes a single error type for
        rendering problems.
        """
        view, _ = self._make(error=RuntimeError(_ENGINE_FAILURE))
        with self.assertRaises(ViewRenderException):
            await view.render()

    async def testRenderPreservesOriginalCause(self) -> None:
        """
        Chain the original failure as the cause of the wrapper.

        Validates that debugging information is never lost when an error
        is re-raised as ViewRenderException.
        """
        original = RuntimeError(_ENGINE_FAILURE)
        view, _ = self._make(error=original)
        with self.assertRaises(ViewRenderException) as ctx:
            await view.render()
        self.assertIs(ctx.exception.__cause__, original)

    async def testRenderErrorMessageNamesTheTemplate(self) -> None:
        """
        Name the failing template in the wrapped error message.

        Validates that the message points developers at the exact view
        that failed.
        """
        view, _ = self._make(error=RuntimeError(_ENGINE_FAILURE))
        with self.assertRaises(ViewRenderException) as ctx:
            await view.render()
        self.assertIn("users.index", str(ctx.exception))

    async def testRenderStripsClosureQualnameNoise(self) -> None:
        """
        Strip closure qualname noise from the wrapped error message.

        Validates that ``<locals>`` fragments leaked by template globals
        never reach the developer-facing message.
        """
        view, _ = self._make(error=RuntimeError(_QUALNAME_FAILURE))
        with self.assertRaises(ViewRenderException) as ctx:
            await view.render()
        message = str(ctx.exception)
        self.assertNotIn("<locals>", message)
        self.assertIn("csrf_field is broken", message)

class TestPendingViewSessionFlashing(TestCase):

    def setUp(self) -> None:
        """
        Replace the session facade with a controllable double.

        Keeps every test isolated from the real container so no booted
        application is required.
        """
        self._original_facade = pending_module.Session
        self._session = _StubSession()
        self._facade = _StubSessionFacade(session=self._session)
        pending_module.Session = self._facade

    def tearDown(self) -> None:
        """
        Restore the original session facade after each test.

        Guarantees that module-level state is never leaked to other
        test cases.
        """
        pending_module.Session = self._original_facade

    def _make(self) -> PendingView:
        """Build a pending view backed by a stub engine."""
        return PendingView(_StubEngine(), "users.index", {})

    async def testRenderSkipsSessionWhenNothingQueued(self) -> None:
        """
        Skip session resolution when no flash data was queued.

        Validates that plain renders never pay the cost of resolving the
        session service.
        """
        await self._make().render()
        self.assertEqual(self._facade.resolved, 0)

    async def testRenderWritesFlashMessagesToSession(self) -> None:
        """
        Write queued flash messages into the active session.

        Validates that status messages become readable through the
        ``flash()`` template global.
        """
        view = self._make().withFlash("status", "saved")
        await view.render()
        self.assertEqual(self._session.messages, {"status": "saved"})

    async def testRenderRoutesOldInputToDedicatedBag(self) -> None:
        """
        Route the old-input bag through the dedicated session method.

        Validates that repopulation data merges instead of overwriting
        anything already flashed during the request.
        """
        view = self._make().withInput({"email": "user@example.com"})
        await view.render()
        self.assertEqual(self._session.inputs, {"email": "user@example.com"})

    async def testRenderRoutesErrorsToDedicatedBag(self) -> None:
        """
        Route the errors bag through the dedicated session method.

        Validates that validation errors merge instead of replacing
        errors flashed earlier in the request.
        """
        view = self._make().withErrors({"email": "invalid"})
        await view.render()
        self.assertEqual(self._session.errors, {"email": ["invalid"]})

    async def testRenderResolvesSessionOnlyOnce(self) -> None:
        """
        Resolve the session exactly once per render.

        Validates that a single write pass carries the whole queued
        payload instead of resolving the service per key.
        """
        view = self._make().withFlash("status", "saved")
        view.withErrors({"email": "invalid"})
        await view.render()
        self.assertEqual(self._facade.resolved, 1)

    async def testRenderIgnoresUnavailableSession(self) -> None:
        """
        Render normally when no session service can be resolved.

        Validates that routes without the session middleware still
        return a response instead of failing.
        """
        self._facade.failure = RuntimeError(_NO_SESSION)
        view = self._make().withFlash("status", "saved")
        self.assertIsInstance(await view.render(), HTMLResponse)

    async def testRenderSkipsWritesWhenSessionIsUnavailable(self) -> None:
        """
        Skip every flash write when the session cannot be resolved.

        Validates that a failed resolution aborts the write pass instead
        of partially applying it.
        """
        self._facade.failure = RuntimeError(_NO_SESSION)
        await self._make().withFlash("status", "saved").render()
        self.assertEqual(self._session.messages, {})
