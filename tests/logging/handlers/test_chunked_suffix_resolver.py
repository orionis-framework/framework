# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from datetime import UTC, datetime, timedelta
from threading import Lock, Thread
from orionis.logging.handlers.chunked_suffix_resolver import ChunkedSuffixResolver
from orionis.test import TestCase

# Number of concurrent callers used to prove the counter is thread safe.
_CONCURRENT_CALLERS = 20


class TestChunkedSuffixResolverSuffix(TestCase):
    """
    Verify the timestamp and counter used to name log chunks.

    Cover explicit timestamps, the current time, and simultaneous requests.
    """

    def testSuffixUsesTheTimestampAndCounterPattern(self) -> None:
        """
        Verify the initial chunk suffix for a fixed UTC timestamp.

        Check that it includes the date, time, and counter value one.
        """
        moment = datetime(2025, 4, 9, 14, 30, 5, tzinfo=UTC)
        resolver = ChunkedSuffixResolver()
        resolver.tz = UTC
        self.assertEqual(
            resolver.getSuffix(dt=moment),
            "20250409_143005_0001",
        )

    def testSuffixDefaultsToTheCurrentTimestamp(self) -> None:
        """Resolve the current timestamp when no datetime is supplied.

        Validates that the handler can request a suffix without tracking time
        by itself.

        Returns
        -------
        None
            No return value.
        """
        self.assertRegex(
            ChunkedSuffixResolver().getSuffix(),
            r"^\d{8}_\d{6}_\d{4}$",
        )

    def testSuffixCounterGrowsOnEveryCall(self) -> None:
        """
        Verify that successive chunks receive increasing counters.

        Hold the timestamp fixed to exercise several rotations within one second.
        """
        resolver = ChunkedSuffixResolver()
        resolver.tz = UTC
        moment = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        produced = [resolver.getSuffix(dt=moment) for _ in range(3)]
        self.assertEqual(
            produced,
            [
                "20250101_000000_0001",
                "20250101_000000_0002",
                "20250101_000000_0003",
            ],
        )

    def testSuffixCounterIsThreadSafe(self) -> None:
        """Serialise concurrent suffix requests.

        Validates that competing threads never obtain the same counter, which
        would make two chunks share a single file.

        Returns
        -------
        None
            No return value.
        """
        resolver = ChunkedSuffixResolver()
        moment = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        produced: list[str] = []
        guard = Lock()

        def collect() -> None:
            """Store one suffix produced by the resolver.

            Returns
            -------
            None
                No return value.
            """
            suffix = resolver.getSuffix(dt=moment)
            with guard:
                produced.append(suffix)

        workers = [Thread(target=collect) for _ in range(_CONCURRENT_CALLERS)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()

        self.assertEqual(len(set(produced)), _CONCURRENT_CALLERS)


class TestChunkedSuffixResolverRotation(TestCase):
    def testNextRotationIsOneHourAhead(self) -> None:
        """Schedule the next rotation one hour after the supplied moment.

        Validates the fallback schedule of a strategy driven by file size
        rather than by time.

        Returns
        -------
        None
            No return value.
        """
        current = datetime(2025, 4, 9, 10, 0, 0, tzinfo=UTC)
        self.assertEqual(
            ChunkedSuffixResolver().getNextRotationTime(current),
            current + timedelta(hours=1),
        )
