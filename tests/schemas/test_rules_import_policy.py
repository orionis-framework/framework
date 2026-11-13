# ruff: noqa: PT009, S603
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Cold-import probes execute only the current interpreter and fixed code.
import json
import subprocess
import sys
from typing import get_type_hints
from orionis.schemas import rules
from orionis.test import TestCase


class TestRulesImportPolicy(TestCase):
    """Exercise schema rule imports in isolated interpreters."""

    def testExportedRuleAnnotationsResolveAtRuntime(self) -> None:
        """Resolve each distinct public constructor and validation method."""
        inspected = set()
        for name in rules.__all__:
            rule = getattr(rules, name)
            for method_name in ("__init__", "enforce", "validate"):
                method = getattr(rule, method_name)
                if method in inspected:
                    continue
                inspected.add(method)
                with self.subTest(rule=name, method=method_name):
                    self.assertIn("return", get_type_hints(method))

    def testColdPackageDoesNotLoadRules(self) -> None:
        """Leave rule implementations unloaded during package inspection.

        Returns
        -------
        None
            No return value.
        """
        code = (
            "import json, sys\n"
            "import orionis.schemas.rules as rules\n"
            "print(json.dumps({'loaded': [name for name in sys.modules "
            "if name.startswith('orionis.schemas.rules.')], "
            "'visible': set(rules.__all__) <= set(dir(rules))}))\n"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-c", code],
            capture_output=True,
            check=True,
            text=True,
            timeout=15,
        )
        result = json.loads(completed.stdout)
        self.assertEqual(result["loaded"], [])
        self.assertTrue(result["visible"])

    def testSingleRuleExportKeepsOtherRulesUnloaded(self) -> None:
        """Resolve one rule without importing the remaining catalog.

        Returns
        -------
        None
            No return value.
        """
        code = (
            "import json, sys\n"
            "from orionis.schemas.rules import Email\n"
            "from orionis.schemas.rules.email import Email as Direct\n"
            "print(json.dumps({'same': Email is Direct, "
            "'loaded': [name for name in sys.modules "
            "if name.startswith('orionis.schemas.rules.')] }))\n"
        )
        completed = subprocess.run(
            [sys.executable, "-B", "-c", code],
            capture_output=True,
            check=True,
            text=True,
            timeout=15,
        )
        result = json.loads(completed.stdout)
        self.assertTrue(result["same"])
        self.assertEqual(result["loaded"], ["orionis.schemas.rules.email"])
