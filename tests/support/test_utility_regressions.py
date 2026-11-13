# ruff: noqa: PT009, S603
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Execute only a fixed fixture with the active interpreter in the isolated suite.
"""Protect resource ownership and boundary values in support utilities."""

import gc
import inspect
import subprocess
import sys
import weakref
from dataclasses import dataclass, make_dataclass

from orionis.support.entities.base import BaseEntity
from orionis.support.performance.counter import PerformanceCounter
from orionis.support.system.workers import Workers
from orionis.test import TestCase

_REENTRANT_SINGLETON = """
from orionis.support.patterns.singleton.meta import Singleton

class Recursive(metaclass=Singleton):
    def __init__(self, recurse=True):
        if recurse:
            Recursive()

try:
    Recursive()
except RuntimeError as error:
    if 'recurs' not in str(error).lower():
        raise
else:
    raise AssertionError('Recursive construction must fail explicitly.')

instance = Recursive(False)
if Recursive() is not instance:
    raise AssertionError('The constructor failure left singleton state poisoned.')
"""


class TestUtilityRegressions(TestCase):
    """Exercise finite numeric limits and the lifetime of temporary classes."""

    def testCounterContextSignaturesResolveAtRuntime(self) -> None:
        """Expose both context-manager traceback annotations to reflection."""
        for name in ("__exit__", "__aexit__"):
            with self.subTest(method=name):
                signature = inspect.signature(
                    getattr(PerformanceCounter, name),
                    eval_str=True,
                )
                self.assertIn("exc_tb", signature.parameters)

    def testAcceptsFiniteLargeWorkerBudgetsWithoutOverflow(self) -> None:
        """Convert a finite budget even if an intermediate float would overflow."""

        class IsolatedWorkers(Workers):
            """Keep the test budget separate from the process-wide policy."""

        IsolatedWorkers.setRamPerWorker(sys.float_info.max)
        self.assertEqual(IsolatedWorkers.calculate(), 1)

    def testMetadataCacheDoesNotRetainDynamicEntityClasses(self) -> None:
        """Allow a temporary entity class to disappear after its last owner."""
        entity_type = make_dataclass(
            "TemporaryEntity",
            [("value", int, 1)],
            bases=(BaseEntity,),
        )
        reference = weakref.ref(entity_type)
        self.assertEqual(entity_type().getFields()[0]["name"], "value")
        child_type = make_dataclass(
            "ChildEntity",
            [("extra", int, 2)],
            bases=(entity_type,),
        )
        self.assertEqual(
            [item["name"] for item in child_type().getFields()],
            ["value", "extra"],
        )
        del child_type
        del entity_type
        gc.collect()
        self.assertIsNone(reference())

    def testRecursiveFieldMetadataDoesNotKeepItsClassAlive(self) -> None:
        """Release an entity even when its field type refers to the class itself."""
        entity_type = type("RecursiveEntity", (BaseEntity,), {"value": None})
        entity_type.__annotations__ = {"value": entity_type}
        entity_type = dataclass(entity_type)
        reference = weakref.ref(entity_type)
        self.assertEqual(entity_type().getFields()[0]["types"], ["RecursiveEntity"])
        del entity_type
        gc.collect()
        self.assertIsNone(reference())

    def testRecursiveSingletonConstructionFailsAndCanBeRetried(self) -> None:
        """Bound a potential deadlock to an isolated child process."""
        result = subprocess.run(
            [sys.executable, "-B", "-c", _REENTRANT_SINGLETON],
            capture_output=True,
            check=False,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
