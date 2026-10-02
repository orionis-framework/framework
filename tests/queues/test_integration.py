import asyncio
import json
import sys

from orionis.test import TestCase


class TestQueueApplicationIntegration(TestCase):
    """Verify eager providers and public workflows in a real application."""

    __slots__ = ()

    async def testRealApplicationDispatchWorkerFailureAndTransactions(self) -> None:
        """Exercise persisted dispatch, scoped DI, retries, CLI, and transactions."""
        process = await asyncio.create_subprocess_exec(
            sys.executable, "-X", "utf8", "-m", "tests.queues.e2e",
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        try:
            output, errors = await asyncio.wait_for(process.communicate(), timeout=45)
        except TimeoutError:
            process.kill()
            await process.wait()
            raise
        self.assertEqual(process.returncode, 0, (output + errors).decode("utf-8"))
        result_line = next(
            (line for line in output.decode("utf-8").splitlines()
             if line.startswith("ORIONIS_QUEUE_E2E=")),
        )
        result = json.loads(result_line.partition("=")[2])
        self.assertEqual(result["driver"], "database")
        self.assertEqual(result["job_discovery"], "app_jobs")
        self.assertEqual(result["success_jobs"], 3)
        self.assertEqual(result["scoped_services"], 3)
        self.assertEqual(result["failure_attempts"], 6)
        self.assertEqual(result["cli"], "work/failed/retry/forget/clear")
