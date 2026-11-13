# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect failure metadata reflection and ownership of deferred effects."""

from __future__ import annotations

import asyncio
import inspect
from typing import TYPE_CHECKING, get_type_hints

from orionis.failure.entities.context import FailureContext
from orionis.failure.entities.handling import FailureHandling
from orionis.failure.entities.throwable import Throwable
from orionis.test import TestCase

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable


def _recursive_callback(
    effect: str,
    handling: FailureHandling,
    calls: list[str],
) -> Callable[..., Awaitable[None]]:
    """Bind one plan and callback counter independently of other scenarios."""

    async def callback(**_kwargs: object) -> None:
        """Reenter the same deferred effect from its owner task."""
        calls.append(effect)
        if effect == "logging":
            await handling.complete()
        else:
            await handling.present(flow="http")

    return callback


class TestFailureContractRegressions(TestCase):
    """Inspect real entity types and execute callbacks through the actual plan."""

    def testEntityAnnotationsResolveAtRuntime(self) -> None:
        """Keep public fields and generated constructor annotations available."""
        for entity, field in (
            (FailureContext, "metadata"),
            (FailureHandling, "logging"),
            (Throwable, "traceback"),
        ):
            with self.subTest(entity=entity.__name__):
                hints = get_type_hints(entity)
                signature = inspect.signature(entity, eval_str=True)
                self.assertEqual(signature.parameters[field].annotation, hints[field])

    async def testRecursiveEffectsFailWithoutRepeatingCallbacks(self) -> None:
        """Reject an owner waiting on its own unfinished effect instead of hanging."""
        for effect in ("logging", "presentation"):
            with self.subTest(effect=effect):
                calls = []
                handling = FailureHandling()
                setattr(handling, effect, _recursive_callback(effect, handling, calls))
                for _ in range(2):
                    pending = (
                        handling.complete()
                        if effect == "logging"
                        else handling.present(flow="http")
                    )
                    with self.assertRaisesRegex(RuntimeError, "[Rr]ecurs"):
                        await asyncio.wait_for(pending, timeout=1)
                self.assertEqual(calls, [effect])

    async def testRepeatedFailuresPreserveIdentityAndBoundTracebacks(self) -> None:
        """Retain the original error and cause without chaining each cached raise."""
        for effect in ("logging", "presentation"):
            with self.subTest(effect=effect):
                original = ValueError("deferred effect")
                cause = LookupError("original cause")
                original.__cause__ = cause

                async def callback(
                    error: BaseException = original,
                    **_kwargs: object,
                ) -> None:
                    """Raise the same original error from the deferred action."""
                    raise error

                handling = FailureHandling(**{effect: callback})
                depths = []
                for _ in range(6):
                    try:
                        if effect == "logging":
                            await handling.complete()
                        else:
                            await handling.present(flow="http")
                    except ValueError as error:
                        self.assertIs(error, original)
                        self.assertIs(error.__cause__, cause)
                        depth = 0
                        traceback = error.__traceback__
                        while traceback is not None:
                            depth += 1
                            traceback = traceback.tb_next
                        depths.append(depth)
                    else:
                        self.fail("A failed effect must retain its original error.")
                self.assertEqual(depths[1:], [depths[1]] * 5)
