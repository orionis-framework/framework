# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Self
from orionis.database import Connection
from orionis.http.default.controllers import register_controller as module
from orionis.http.default.schemas.register import RegisterSchema
from orionis.http.responses import Response
from orionis.test import TestCase
from tests.auth.test_password_reset import _View
from tests.http.test_kernel import make_request_double
from tests.http.test_support import replace_attribute
from tests.foundation.test_application_async import _AsyncCall


class _RegistrationView(_View):
    """Capture registration errors without rendering an application template."""

    def withInput(self, data: dict) -> Self:
        """Retain the submitted form fields independently of the error message.

        Parameters
        ----------
        data : dict
            Submitted form fields.

        Returns
        -------
        Self
            This pending response.
        """
        self.context["input"] = data
        return self


def _registration_user(
    db: Connection,
    failure: BaseException | None,
    *,
    saved: bool,
) -> type:
    """Build a model fixture whose persistence uses the supplied native connection.

    Parameters
    ----------
    db : Connection
        Test-owned in-memory connection.
    failure : BaseException | None
        Failure injected after insertion.
    saved : bool
        Whether persistence is permitted.

    Returns
    -------
    type
        User factory consumed by the registration controller.
    """

    class User:
        """Persist only the field needed to verify atomicity."""

        name: str
        email: str
        password: str

        async def save(self) -> bool:
            """Write a real row before the selected post-insert failure.

            Returns
            -------
            bool
                Whether persistence is allowed by this model.
            """
            if not saved:
                return False
            await db.execute(
                "INSERT INTO registrations (name) VALUES (:name)",
                {"name": self.name},
            )
            if failure is not None:
                raise failure
            return True

    return User


class TestRegistrationLifecycle(TestCase):
    """Exercise controller transactions against owned in-memory SQLite."""

    async def testEmailVerificationCannotReportSuccessAfterAPersistenceVeto(
        self,
    ) -> None:
        """Do not show a verified state when the model refuses its update.

        Returns
        -------
        None
            No return value.
        """
        user = SimpleNamespace(
            active=False,
            email_verified_at=None,
            freshTimestamp=lambda: datetime(2026, 1, 1, tzinfo=UTC),
            save=_AsyncCall(return_value=False),
        )
        states = []

        def view(_name: str, **context: object) -> _View:
            """Record the verification state presented to the browser.

            Parameters
            ----------
            _name : str
                Verification template name.
            **context : object
                Template context supplied by the controller.

            Returns
            -------
            _View
                Awaitable response recorder.
            """
            states.append(context["state"])
            return _View(context)

        with (
            replace_attribute(
                module.RegisterController,
                "_RegisterController__resolveUser",
                _AsyncCall(return_value=user),
            ),
            replace_attribute(module, "response", SimpleNamespace(view=view)),
            self.assertRaisesRegex(RuntimeError, "could not be verified"),
        ):
            await module.RegisterController().verifyEmail(
                make_request_double("/verify-email"),
            )
        self.assertEqual(user.save.awaitCount, 1)
        self.assertEqual(states, [])

    async def testRegistrationRollsBackFailureCancellationAndPersistenceVeto(
        self,
    ) -> None:
        """Persist only successful registrations and keep backend details private.

        Returns
        -------
        None
            No return value.
        """

        async def check(failure: BaseException | None, *, saved: bool) -> None:
            """Run one registration outcome in an independent native transaction.

            Parameters
            ----------
            failure : BaseException | None
                Failure raised after a test-owned insertion.
            saved : bool
                Whether the model allows persistence.

            Returns
            -------
            None
                No return value.
            """
            db = Connection(
                "registration",
                {"driver": "sqlite", "database": ":memory:"},
            )
            form = _RegistrationView({})

            async def make_hash(_value: str) -> str:
                """Return a synthetic hash without exercising a hashing backend.

                Parameters
                ----------
                _value : str
                    Password supplied by the controller.

                Returns
                -------
                str
                    Test-owned hash placeholder.
                """
                return "synthetic-hash"

            def view(_name: str) -> _RegistrationView:
                """Return the response boundary used to inspect field errors.

                Parameters
                ----------
                _name : str
                    Registration template name.

                Returns
                -------
                _RegistrationView
                    Awaitable field-error recorder.
                """
                return form

            gateway = SimpleNamespace(
                beginTransaction=db.begin,
                commit=db.commit,
                rollback=db.rollback,
                transaction=db.transaction,
            )
            credential = "SyntheticPassword9!"
            payload = RegisterSchema(
                name="Example User",
                email="example@example.test",
                password=credential,
                password_confirmation=credential,
            )
            try:
                await db.statement("CREATE TABLE registrations (name TEXT NOT NULL)")
                with (
                    replace_attribute(module, "DB", gateway),
                    replace_attribute(
                        module,
                        "User",
                        _registration_user(db, failure, saved=saved),
                    ),
                    replace_attribute(module, "Hash", SimpleNamespace(make=make_hash)),
                    replace_attribute(
                        module,
                        "response",
                        SimpleNamespace(
                            view=view,
                            redirect=module.response.redirect,
                        ),
                    ),
                ):
                    controller = module.RegisterController()
                    request = make_request_double("/sign-up")
                    if isinstance(failure, asyncio.CancelledError):
                        with self.assertRaises(asyncio.CancelledError) as caught:
                            await controller.register(payload, request)
                        self.assertIs(caught.exception, failure)
                    else:
                        response = await controller.register(payload, request)
                        self.assertIsInstance(response, Response)
                        if failure is None and saved:
                            self.assertEqual(response.getStatusCode(), 302)
                        else:
                            self.assertEqual(
                                form.errors,
                                {
                                    "registration": (
                                        "The account could not be created. "
                                        "Please try again."
                                    ),
                                },
                            )
                self.assertFalse(db.inTransaction())
                self.assertEqual(
                    await db.select("SELECT name FROM registrations"),
                    [{"name": "Example User"}] if failure is None and saved else [],
                )
            finally:
                if db.inTransaction():
                    await db.rollback()
                await db.disconnect()

        for failure, saved in (
            (None, True),
            (ValueError("private database parameters"), True),
            (asyncio.CancelledError("cancelled registration"), True),
            (None, False),
        ):
            with self.subTest(failure=type(failure), saved=saved):
                await check(failure, saved=saved)
