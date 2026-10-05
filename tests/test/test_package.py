import subprocess
import sys
from pathlib import Path
import orionis.test as test_package
from orionis.test import TestCase
from orionis.test.cases.case import TestCase as CoreTestCase
from orionis.test.clients.mcp import McpTestClient, McpTestResponse

class TestPackage(TestCase):
    """Verify the public testing API and its deferred protocol imports."""

    def testPublicExportsResolveToTheirNativeImplementations(self) -> None:
        """Expose the test case and MCP helpers from one public package.

        Returns
        -------
        None
            Verify every declared export resolves to its native implementation.
        """
        self.assertEqual(
            {name: getattr(test_package, name) for name in test_package.__all__},
            {
                "TestCase": CoreTestCase,
                "McpTestClient": McpTestClient,
                "McpTestResponse": McpTestResponse,
            },
        )

    def testOrdinaryTestCaseImportDoesNotLoadMcp(self) -> None:
        """Keep protocol dependencies unloaded for ordinary test cases.

        Returns
        -------
        None
            Verify the import boundary in a fresh interpreter.
        """
        source = (
            "import sys\n"
            "from orionis.test import TestCase\n"
            "assert callable(TestCase.mcp)\n"
            "assert not any(name == 'orionis.mcp' "
            "or name.startswith('orionis.mcp.') for name in sys.modules)\n"
        )
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-B", "-c", source],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
