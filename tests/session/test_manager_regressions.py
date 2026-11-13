# ruff: noqa: PT009, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Preserve cookie identity during expiry and resolve manager annotations."""

import inspect
from http.cookies import SimpleCookie
from pathlib import Path
from typing import get_type_hints
from orionis.http.responses import JSONResponse
from orionis.session.manager import SessionManager
from orionis.session.session import Session
from orionis.test import TestCase
from tests.session.test_manager import _FakeApplication, _make_config


class TestSessionManagerRegressions(TestCase):
    """Exercise configured cookie policies using real response serialization."""

    async def testExpirationPreservesTheConfiguredCookieIdentity(self) -> None:
        """Expire secure and partitioned cookies with the same policy as issuance.

        Returns
        -------
        None
            No return value.
        """
        for options in (
            {"cookie": "__Host-session", "secure": True, "same_site": "none"},
            {
                "cookie": "partitioned-session",
                "secure": True,
                "partitioned": True,
                "same_site": "none",
                "domain": "example.test",
                "path": "/app",
            },
        ):
            with self.subTest(options=options):
                config = _make_config(options)
                manager = SessionManager(_FakeApplication(config, Path()), None)
                session = Session()
                session.put("account", 7)
                issued_response = JSONResponse({})
                await manager.save(issued_response, session)
                session.invalidate()
                expired_response = JSONResponse({})
                await manager.save(expired_response, session)
                issued = SimpleCookie(issued_response.getHeader("set-cookie")[0])
                expired = SimpleCookie(expired_response.getHeader("set-cookie")[0])
                name = config["cookie"]
                self.assertEqual(expired[name].value, "")
                self.assertEqual(expired[name]["max-age"], "0")
                self.assertEqual(
                    expired[name]["expires"],
                    "Thu, 01 Jan 1970 00:00:00 GMT",
                )
                for attribute in (
                    "path",
                    "domain",
                    "secure",
                    "httponly",
                    "samesite",
                    "partitioned",
                ):
                    with self.subTest(attribute=attribute):
                        self.assertEqual(
                            expired[name][attribute],
                            issued[name][attribute],
                        )
                self.assertIsNone(await manager._store.read(session.id))

    def testManagerAnnotationsResolveWithoutCallerNamespaces(self) -> None:
        """Evaluate each manager function's runtime types without injected imports.

        Returns
        -------
        None
            No return value.
        """
        get_type_hints(SessionManager)
        for name, member in vars(SessionManager).items():
            function = member.fget if isinstance(member, property) else member
            if inspect.isfunction(function):
                with self.subTest(member=name):
                    get_type_hints(function)
