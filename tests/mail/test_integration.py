import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.test import TestCase

_ROOT = Path(__file__).resolve().parents[2]

class TestMailApplicationIntegration(TestCase):
    async def _runApplication(self, runtime: str) -> dict[str, object]:
        """Execute the isolated application with the active dependency search path.

        Parameters
        ----------
        runtime : str
            HTTP or CLI entry point exercised by the subprocess fixture.

        Returns
        -------
        dict[str, object]
            Mail example results reported by the isolated application.
        """
        root = _ROOT
        fixture = root / "tests/mail/fixtures/application.py"
        with TemporaryDirectory() as temporary:
            paths = [temporary, str(root)]
            inherited_path = os.environ.get("PYTHONPATH")
            if inherited_path:
                paths.append(inherited_path)
            environment = {
                **os.environ,
                "PYTHONPATH": os.pathsep.join(paths),
                "PYTHONIOENCODING": "utf-8",
            }
            result = await asyncio.to_thread(
                subprocess.run, [sys.executable, str(fixture), runtime],
                cwd=temporary, env=environment, check=False,
                capture_output=True, text=True, encoding="utf-8", timeout=45,
            )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout.strip().splitlines()[-1])

    async def testAllExamplesAfterNormalHttpLifespanStartup(self) -> None:
        """Execute every required example after a fresh real HTTP startup.

        Returns
        -------
        None
            Examples and the facade lifecycle are verified in the child process.
        """
        result = await self._runApplication("http")
        self.assertEqual(result["files"], 18)
        self.assertEqual(result["extension"], "recording")
        self.assertTrue(result["facade_pinned"])

    async def testAllExamplesAfterNormalCliStartup(self) -> None:
        """Execute every required example after a fresh real CLI startup.

        Returns
        -------
        None
            Examples and the facade lifecycle are verified in the child process.
        """
        result = await self._runApplication("cli")
        self.assertEqual(result["files"], 18)
        self.assertEqual(result["extension"], "recording")
        self.assertTrue(result["facade_pinned"])
