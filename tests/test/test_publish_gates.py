import json
import shutil
import subprocess
import tempfile
from pathlib import Path
from orionis.test import TestCase

_PUBLISH_WRAPPER = r"""
param([string]$FailureKind)
$ErrorActionPreference = "Stop"
$global:failureKind = $FailureKind
$global:callLog = Join-Path $PSScriptRoot "calls.jsonl"
function global:uv {
    $commandText = $args -join " "
    $record = @{ tool = "uv"; arguments = $commandText }
    Add-Content -LiteralPath $global:callLog -Value (
        $record | ConvertTo-Json -Compress
    )
    $global:LASTEXITCODE = 0
    if ($global:failureKind -eq "tests" -and
        $commandText -match "reactor test|run_tests.py") {
        $global:LASTEXITCODE = 1
    }
    if ($global:failureKind -eq "lint" -and
        $commandText -match "ruff check") {
        $global:LASTEXITCODE = 1
    }
    if ($global:failureKind -eq "lock" -and $commandText -eq "lock") {
        $global:LASTEXITCODE = 1
    }
}
function global:git {
    $commandText = $args -join " "
    $record = @{ tool = "git"; arguments = $commandText }
    Add-Content -LiteralPath $global:callLog -Value (
        $record | ConvertTo-Json -Compress
    )
    $global:LASTEXITCODE = 0
    if ($commandText -match "status --porcelain") { " M fixture.py" }
    if ($commandText -match "rev-list") { "1" }
}
function global:sonar-scanner { $global:LASTEXITCODE = 0 }
function global:chcp { $global:LASTEXITCODE = 0 }
& (Join-Path $PSScriptRoot "PUBLISH.ps1") -ContinueOnError
exit $LASTEXITCODE
"""


class TestPublishGates(TestCase):
    """Protect mandatory validation before commit and push."""

    def setUp(self) -> None:
        """Locate the local publisher and its PowerShell interpreter.

        Returns
        -------
        None
            Skip the local script checks when either prerequisite is absent.
        """
        self.publish_script = Path(__file__).resolve().parents[2] / "PUBLISH.ps1"
        if not self.publish_script.is_file():
            self.skipTest("PUBLISH.ps1 is a local utility absent from this checkout.")
        self.powershell = shutil.which("pwsh")
        if self.powershell is None:
            self.skipTest("PowerShell 7 is required to execute PUBLISH.ps1.")

    def _runPublish(
        self,
        failure_kind: str,
    ) -> tuple[subprocess.CompletedProcess[str], list[dict[str, str]]]:
        """Run an isolated script copy with explicit command doubles.

        Parameters
        ----------
        failure_kind : str
            Mandatory gate to fail, or ``none`` for successful validation.

        Returns
        -------
        tuple[subprocess.CompletedProcess[str], list[dict[str, str]]]
            Process output and recorded command invocations.
        """
        with tempfile.TemporaryDirectory(prefix="orionis-publish-gates-") as root:
            directory = Path(root)
            shutil.copy2(self.publish_script, directory / "PUBLISH.ps1")
            wrapper = directory / "wrapper.ps1"
            wrapper.write_text(_PUBLISH_WRAPPER, encoding="utf-8")
            result = subprocess.run(  # noqa: S603
                [self.powershell, "-NoProfile", "-File", str(wrapper), failure_kind],
                cwd=directory,
                capture_output=True,
                text=True,
                encoding="utf-8-sig",
                check=False,
                timeout=30,
            )
            log = directory / "calls.jsonl"
            calls = (
                [
                    json.loads(line)
                    for line in log.read_text(encoding="utf-8-sig").splitlines()
                ]
                if log.exists()
                else []
            )
            return result, calls

    def testPublicationRequiresEveryMandatoryGate(self) -> None:
        """Block publication after any failed gate despite ContinueOnError.

        Returns
        -------
        None
            Assertions verify exit codes, remaining validation and Git calls.
        """
        for failure_kind in ("tests", "lint", "lock", "none"):
            with self.subTest(gate=failure_kind):
                result, calls = self._runPublish(failure_kind)
                output = result.stdout + result.stderr
                self.assertEqual(result.returncode, int(failure_kind != "none"), output)
                uv_calls = [call["arguments"] for call in calls if call["tool"] == "uv"]
                self.assertIn("lock", uv_calls, output)
                self.assertIn(
                    "run python -B .github/scripts/run_tests.py --continue-on-error",
                    uv_calls,
                    output,
                )
                self.assertIn(
                    "run ruff check ./orionis/ --statistics", uv_calls, output,
                )
                git_calls = [
                    call["arguments"] for call in calls if call["tool"] == "git"
                ]
                if failure_kind == "none":
                    self.assertTrue(
                        any(" add " in call for call in git_calls), output,
                    )
                    self.assertTrue(
                        any(" commit -m " in call for call in git_calls), output,
                    )
                    self.assertTrue(
                        any(call.endswith(" push") for call in git_calls), output,
                    )
                else:
                    self.assertEqual(git_calls, [], output)
