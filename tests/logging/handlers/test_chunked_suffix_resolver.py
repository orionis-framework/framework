from datetime import UTC, datetime, timedelta
from threading import Lock, Thread
from orionis.logging.handlers.chunked_suffix_resolver import ChunkedSuffixResolver
from orionis.test import TestCase

# Number of concurrent callers used to prove the counter is thread safe.
_CONCURRENT_CALLERS = 20

class TestChunkedSuffixResolverSuffix(TestCase):

    def testSuffixUsesTheTimestampAndCounterPattern(self) -> None:
        """
        Build the suffix from the timestamp and an incremental counter.

        Validates the naming scheme that keeps every size based chunk unique.
        """
        moment = datetime(2025, 4, 9, 14, 30, 5, tzinfo=UTC)
        self.assertEqual(
            ChunkedSuffixResolver().getSuffix(dt=moment),
            "20250409_143005_0001",
        )

    def testSuffixDefaultsToTheCurrentTimestamp(self) -> None:
        """
        Resolve the current timestamp when no datetime is supplied.

        Validates that the handler can request a suffix without tracking time
        by itself.
        """
        self.assertRegex(
            ChunkedSuffixResolver().getSuffix(),
            r"^\d{8}_\d{6}_\d{4}$",
        )

    def testSuffixCounterGrowsOnEveryCall(self) -> None:
        """
        Increment the counter on every suffix request.

        Validates that two chunks written within the same second never share a
        file name.
        """
        resolver = ChunkedSuffixResolver()
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
        """
        Serialise concurrent suffix requests.

        Validates that competing threads never obtain the same counter, which
        would make two chunks share a single file.
        """
        resolver = ChunkedSuffixResolver()
        moment = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        produced: list[str] = []
        guard = Lock()

        def collect() -> None:
            """Store one suffix produced by the resolver."""
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
        """
        Schedule the next rotation one hour after the supplied moment.

        Validates the fallback schedule of a strategy driven by file size
        rather than by time.
        """
        current = datetime(2025, 4, 9, 10, 0, 0, tzinfo=UTC)
        self.assertEqual(
            ChunkedSuffixResolver().getNextRotationTime(current),
            current + timedelta(hours=1),
        )
