import base64
import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from orionis.console.commands.bootstrap._config import _RAW_ROOT, _TREE_URL

_ROOT = Path(__file__).resolve().parents[4]
_DRIVER = r"""
import base64
import json
import runpy
import sys
from io import BytesIO
from unittest.mock import patch

entry, reactor, fixtures, *arguments = sys.argv[1:]
responses = json.loads(fixtures)

class Response(BytesIO):
    status = 200

def request(resource, *, timeout):
    return Response(base64.b64decode(responses[resource.full_url]))

with patch("orionis.console.commands.bootstrap._config.urlopen", request):
    if entry == "console":
        sys.argv = ["orionis", *arguments]
        from orionis.console.cli import main
        raise SystemExit(main())
    sys.argv = [reactor, *arguments]
    runpy.run_path(reactor, run_name="__main__")
"""


class TestBootstrapConfigCli(unittest.TestCase):
    """Exercise optional configuration selection through both real CLI launchers."""

    def setUp(self) -> None:
        """
        Prepare a disposable application without inherited command caches.

        Returns
        -------
        None
            Create the application bootstrap and register temporary-file cleanup.
        """
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        bootstrap = self.root / "bootstrap" / "app.py"
        bootstrap.parent.mkdir()
        bootstrap.write_text(
            "from pathlib import Path\n"
            "from orionis import Application\n"
            "app = Application(base_path=Path(__file__).parent.parent)\n"
            "app.create()\n",
            encoding="utf-8",
        )
        self.reactor = self.root / "reactor"
        self.reactor.write_bytes((_ROOT / "reactor").read_bytes())

    def _run(
        self,
        entry: str,
        files: dict[str, bytes],
        *arguments: str,
    ) -> subprocess.CompletedProcess[str]:
        """
        Run native CLI dispatch with deterministic, offline GitHub responses.

        Parameters
        ----------
        entry : str
            Either the installed console-script entry point or the Reactor file.
        files : dict[str, bytes]
            Remote configuration paths and their exact advertised contents.
        *arguments : str
            CLI arguments forwarded unchanged to the selected entry point.

        Returns
        -------
        subprocess.CompletedProcess[str]
            Completed subprocess containing its exit code and terminal output.
        """
        entries = [
            {
                "path": path,
                "type": "blob",
                "mode": "100644",
                "size": len(content),
                "sha": hashlib.sha1(
                    f"blob {len(content)}\0".encode() + content,
                ).hexdigest(),
            }
            for path, content in files.items()
        ]
        responses = {
            _RAW_ROOT + path: base64.b64encode(content).decode("ascii")
            for path, content in files.items()
        }
        responses[_TREE_URL] = base64.b64encode(
            json.dumps({"truncated": False, "tree": entries}).encode(),
        ).decode("ascii")
        return subprocess.run(  # noqa: S603
            [
                sys.executable, "-B", "-c", _DRIVER,
                entry, str(self.reactor), json.dumps(responses), *arguments,
            ],
            cwd=self.root,
            env={
                **os.environ,
                "PYTHONPATH": str(_ROOT),
                "PYTHONDONTWRITEBYTECODE": "1",
                "PYTHONUTF8": "1",
                "NO_COLOR": "1",
            },
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=45,
            check=False,
        )

    def test_help_exposes_optional_file_without_creating_configuration(self) -> None:
        """
        Show the optional positional argument without downloading configuration.

        Returns
        -------
        None
            Assert help succeeds and leaves configuration resources absent.
        """
        for entry in ("console", "reactor"):
            with self.subTest(entry=entry):
                result = self._run(entry, {}, "bootstrap:config", "--help")

                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("Arguments (Positional)", result.stdout)
                self.assertRegex(result.stdout, r"file\s+str\s+No")
                self.assertFalse((self.root / "config").exists())

    def test_selected_remote_file_is_created_once_and_preserves_local_changes(
        self,
    ) -> None:
        """
        Select a remotely discovered file and preserve subsequent local edits.

        Returns
        -------
        None
            Assert both launchers restore only the selected file without rewrites.
        """
        files = {
            "config/future.py": b"# Official future configuration\r\n",
            "config/mail.py": b"# Unselected mail configuration\n",
        }
        created = self._run("console", files, "bootstrap:config", "future")

        self.assertEqual(created.returncode, 0, created.stdout + created.stderr)
        self.assertIn("CREATED", created.stdout)
        destination = self.root / "config" / "future.py"
        self.assertEqual(destination.read_bytes(), files["config/future.py"])
        self.assertFalse((self.root / "config" / "mail.py").exists())
        destination.write_bytes(b"# Local configuration customizations\n")
        original = destination.read_bytes(), destination.stat().st_mtime_ns

        repeated = self._run("reactor", files, "bootstrap:config", "future")

        self.assertEqual(repeated.returncode, 0, repeated.stdout + repeated.stderr)
        self.assertIn("EXISTS", repeated.stdout)
        self.assertEqual(
            (destination.read_bytes(), destination.stat().st_mtime_ns), original,
        )
        self.assertFalse((self.root / "config" / "mail.py").exists())

    def test_unknown_file_reports_current_remote_options_without_writes(self) -> None:
        """
        Report a missing selection using the actual remote configuration catalog.

        Returns
        -------
        None
            Assert failures include remote choices and leave configuration absent.
        """
        files = {
            "config/app.py": b"# Application configuration\n",
            "config/future.py": b"# Future configuration\n",
        }
        for entry in ("console", "reactor"):
            with self.subTest(entry=entry):
                result = self._run(entry, files, "bootstrap:config", "missing")

                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("missing", result.stdout)
                self.assertIn("app", result.stdout)
                self.assertIn("future", result.stdout)
                self.assertNotIn("CREATED", result.stdout)
                self.assertFalse((self.root / "config").exists())
