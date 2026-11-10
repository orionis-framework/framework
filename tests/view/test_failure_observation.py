"""Distinguish unavailable request scope from broken registered view services."""

from unittest.mock import AsyncMock, MagicMock, patch
from orionis.container.container import Container
from orionis.session.contracts.session import ISession
from orionis.view.globals.session import _global_session
from tests.support.failure_runtime import IsolatedFailureTestCase, activate_runtime


class TestViewFailureObservation(IsolatedFailureTestCase):
    """Observe failed service resolution while preserving optional fallbacks."""

    async def testNoSessionBindingRemainsAnOrdinaryFallback(self) -> None:
        """Rendering without a request does not report a missing session."""
        app, _, handler = activate_runtime()
        with patch.object(Container, "make", AsyncMock(side_effect=ValueError)):
            self.assertIsNone(await _global_session(app)())
        self.assertEqual(handler.failures, [])

    async def testBrokenSessionBindingReportsOriginalFailure(self) -> None:
        """Report a registered session provider failure and retain None."""
        app, _, handler = activate_runtime()
        app.instance(ISession, MagicMock(spec=ISession))
        error = OSError("registered provider failed")
        with patch.object(Container, "make", AsyncMock(side_effect=error)):
            self.assertIsNone(await _global_session(app)())
        self.assertEqual(handler.reports, [error])

    async def testBindingInspectionCannotHideOriginalFailure(self) -> None:
        """Observe both errors if inspecting a failing container also fails."""
        app, _, handler = activate_runtime()
        error, inspection = OSError("resolve"), RuntimeError("inspection")
        with (
            patch.object(Container, "make", AsyncMock(side_effect=error)),
            patch.object(Container, "bound", side_effect=inspection),
        ):
            self.assertIsNone(await _global_session(app)())
        self.assertEqual(handler.reports, [inspection, error])
