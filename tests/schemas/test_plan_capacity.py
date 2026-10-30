import gc
import weakref
from typing import Self
from unittest.mock import patch
import msgspec
from orionis.schemas import rules_executor
from orionis.test import TestCase

class TestPlanCapacity(TestCase):
    """Bound class retention even when rules can reference schema types."""

    def testEvictedDynamicSchemasAreCollectable(self: Self) -> None:
        """
        Compile more types than capacity and release evicted classes.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        references = []
        original = rules_executor._PLAN_CACHE.copy()
        try:
            rules_executor._PLAN_CACHE.clear()
            with patch.object(rules_executor, "_PLAN_CACHE_MAX", 16):
                for index in range(200):
                    schema = msgspec.defstruct(f"Dynamic{index}", [("value", int)])
                    rules_executor._build_plan(schema)
                    references.append(weakref.ref(schema))
                del schema
                gc.collect()
                self.assertEqual(len(rules_executor._PLAN_CACHE), 16)
                self.assertLessEqual(sum(ref() is not None for ref in references), 16)
        finally:
            rules_executor._PLAN_CACHE.clear()
            rules_executor._PLAN_CACHE.update(original)
