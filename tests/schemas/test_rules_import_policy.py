import json
import subprocess
import sys
from orionis.test import TestCase

class TestRulesImportPolicy(TestCase):
    """Exercise schema rule imports in isolated interpreters."""

    def testColdPackageDoesNotLoadRules(self) -> None:
        """Leave rule implementations unloaded during package inspection.

        Returns
        -------
        None
            Assertions validate the initial rule import state.
        """
        code = (
            "import json, sys\n"
            "import orionis.schemas.rules as rules\n"
            "print(json.dumps({'loaded': [name for name in sys.modules "
            "if name.startswith('orionis.schemas.rules.')], "
            "'visible': set(rules.__all__) <= set(dir(rules))}))\n"
        )
        completed = subprocess.run(  # noqa: S603
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
            Assertions validate selected rule identity and loaded modules.
        """
        code = (
            "import json, sys\n"
            "from orionis.schemas.rules import Email\n"
            "from orionis.schemas.rules.email import Email as Direct\n"
            "print(json.dumps({'same': Email is Direct, "
            "'loaded': [name for name in sys.modules "
            "if name.startswith('orionis.schemas.rules.')] }))\n"
        )
        completed = subprocess.run(  # noqa: S603
            [sys.executable, "-B", "-c", code],
            capture_output=True,
            check=True,
            text=True,
            timeout=15,
        )
        result = json.loads(completed.stdout)
        self.assertTrue(result["same"])
        self.assertEqual(result["loaded"], ["orionis.schemas.rules.email"])
