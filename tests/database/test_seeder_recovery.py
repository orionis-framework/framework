# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Preserve seeder claim failures when recovery cannot read tracking state."""

from contextlib import asynccontextmanager
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

from orionis.database.exceptions import QueryException
from orionis.database.seeders.runner import SeederRunner
from orionis.database.seeders.seeder import Seeder
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class _UnusedSeeder(Seeder):
    """Represent a discovered step whose claim must fail before execution."""

    async def run(self) -> None:
        """Reject execution when the tracking claim has not succeeded."""
        message = "The failed claim must prevent seeder execution."
        raise AssertionError(message)


class TestSeederRecovery(TestCase):
    """Exercise recovery error handling through the public seeding operation."""

    async def testRecoveryKeepsTheClaimErrorAndItsOriginalCause(self) -> None:
        """Retain claim identity and cause while observing a failed recovery read."""
        for unreadable in (False, True):
            with self.subTest(unreadable=unreadable):
                original = QueryException("The controlled claim failed.")
                cause = OSError("The controlled underlying operation failed.")
                original.__cause__ = cause
                secondary = QueryException("The controlled recovery read failed.")
                exits = []

                @asynccontextmanager
                async def transaction(_exits: list[str] = exits) -> AsyncIterator[None]:
                    """Settle the controlled transaction before claim recovery."""
                    try:
                        yield
                    finally:
                        _exits.append("settled")

                connection = SimpleNamespace(
                    supportsUniqueConstraints=lambda: True,
                    createTable=AsyncMock(return_value=True),
                    select=AsyncMock(side_effect=[[], secondary if unreadable else []]),
                    insert=AsyncMock(side_effect=original),
                    transaction=transaction,
                )
                manager = SimpleNamespace(
                    connection=lambda _name, _connection=connection: _connection,
                )
                runner = SeederRunner(SimpleNamespace(), manager)
                with (
                    patch.object(
                        SeederRunner,
                        "_SeederRunner__discover",
                        return_value={"fixture": _UnusedSeeder},
                    ),
                    patch(
                        "orionis.failure.runtime.capture",
                        new_callable=AsyncMock,
                    ) as capture,
                    self.assertRaises(QueryException) as raised,
                ):
                    await runner.seed()
                self.assertIs(raised.exception, original)
                self.assertIs(raised.exception.__cause__, cause)
                self.assertEqual(exits, ["settled"])
                self.assertEqual(capture.await_count, int(unreadable))
                if unreadable:
                    self.assertIs(capture.await_args.args[0], secondary)
                    self.assertEqual(capture.await_args.kwargs["phase"], "recovery")
