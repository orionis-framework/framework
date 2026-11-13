# ruff: noqa: PT009, PT027, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect hashing parameter bounds and runtime constructor annotations."""

from typing import get_type_hints
from unittest.mock import patch

from orionis.hashing.exceptions import HashConfigurationException
from orionis.hashing.hashers.argon2_hasher import Argon2Hasher
from orionis.hashing.hashers.bcrypt_hasher import BcryptHasher
from orionis.support.concurrency import BoundedExecutor
from orionis.test import TestCase

_VALID_OPTIONS = {"memory": 32, "threads": 1, "time": 1}
"""Use small valid costs without changing the framework's secure defaults."""


class TestHashingParameterValidation(TestCase):
    """Validate native parameter boundaries before constructing a backend."""

    def testConstructorAnnotationsResolve(self) -> None:
        """Resolve optional executor annotations used by runtime introspection."""
        for driver in (Argon2Hasher, BcryptHasher):
            with self.subTest(driver=driver.__name__):
                hints = get_type_hints(driver.__init__)
                self.assertEqual(hints["executor"], BoundedExecutor | None)

    async def testRejectsUnsupportedArgon2Parameters(self) -> None:
        """Reject impossible costs without mutating defaults or reaching native work.

        Prevent backend construction because the invalid cases include values
        that could consume excessive resources if mistakenly accepted.
        """
        invalid_options = (
            {"memory": 7},
            {"threads": 5},
            {"memory": 2**32},
            {"time": 2**32},
            {"memory": 2**27, "threads": 2**24},
        )
        for options in invalid_options:
            with (
                self.subTest(operation="construct", options=options),
                self.assertRaises(HashConfigurationException),
            ):
                Argon2Hasher(**{**_VALID_OPTIONS, **options})

        invalid_setters = (
            ("setMemory", 7),
            ("setThreads", 5),
            ("setMemory", 2**32),
            ("setRounds", 2**32),
            ("setThreads", 2**24),
        )
        for name, value in invalid_setters:
            with self.subTest(operation=name, value=value):
                hasher = Argon2Hasher(**_VALID_OPTIONS)
                original = (hasher._memory, hasher._threads, hasher._time)
                with self.assertRaises(HashConfigurationException):
                    getattr(hasher, name)(value)
                self.assertEqual(
                    (hasher._memory, hasher._threads, hasher._time),
                    original,
                )

        with patch.object(
            Argon2Hasher,
            "_build",
            side_effect=AssertionError("Invalid costs reached the native backend."),
        ):
            for options in invalid_options:
                overrides = {
                    "rounds" if name == "time" else name: value
                    for name, value in options.items()
                }
                with self.subTest(operation="make", options=overrides):
                    hasher = Argon2Hasher(**_VALID_OPTIONS)
                    with self.assertRaises(HashConfigurationException):
                        await hasher.make("local-validation", **overrides)
