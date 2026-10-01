import asyncio
import time
from unittest.mock import patch
from orionis.support.performance.counter import PerformanceCounter
from orionis.test import TestCase

class TestPerformanceCounterSync(TestCase):
    # ------------------------------------------------ start / stop

    def testStartReturnsSelf(self):
        """Return self from start for method chaining.

        Validates that start() returns the same PerformanceCounter
        instance to allow fluent method chaining.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        result = counter.start()
        self.assertIs(result, counter)

    def testStopReturnsSelf(self):
        """Return self from stop for method chaining.

        Validates that stop() returns the same PerformanceCounter
        instance after recording the elapsed time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        result = counter.stop()
        self.assertIs(result, counter)

    def testStartAndStopProducePositiveElapsedTime(self):
        """Produce a positive elapsed time after start and stop.

        Validates that calling start() followed by stop() results in
        a positive elapsed time value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        time.sleep(0.01)
        counter.stop()
        self.assertGreater(counter.elapsedTime(), 0)

    def testStartClearsPreviousMeasurement(self):
        """Clear the prior result when a new measurement starts.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with patch(
            "orionis.support.performance.counter.time.perf_counter",
            side_effect=(1.0, 2.0, 3.0),
        ):
            counter = PerformanceCounter()
            counter.start()
            counter.stop()
            counter.start()
            with self.assertRaises(ValueError):
                counter.elapsedTime()

    def testStopBeforeStartRaisesValueError(self):
        """Reject a stop call when no measurement has started.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            PerformanceCounter().stop()

    def testElapsedTimeIsFloat(self):
        """Return elapsed time as a float.

        Validates that elapsedTime() returns a float value after the
        counter has been started and stopped.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        counter.stop()
        self.assertIsInstance(counter.elapsedTime(), float)

    def testElapsedTimeRaisesBeforeStop(self):
        """Raise ValueError when elapsed time is requested before stop.

        Validates that calling elapsedTime() before stop() raises a
        ValueError since the counter has not completed a cycle.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        with self.assertRaises(ValueError):
            counter.elapsedTime()

    def testElapsedTimeRaisesWithoutStartAndStop(self):
        """Raise ValueError when elapsed time is requested without any measurement.

        Validates that calling elapsedTime() on a fresh counter that
        has never been started raises a ValueError.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        with self.assertRaises(ValueError):
            counter.elapsedTime()

    async def testStopRaisesAfterAstart(self):
        """Raise RuntimeError when stop is called after astart.

        Validates that mixing sync stop() with async astart() raises
        a RuntimeError to prevent incorrect usage.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        await counter.astart()
        with self.assertRaises(RuntimeError):
            counter.stop()

    # ------------------------------------------------ unit conversions

    def testGetMicrosecondsReturnsPositive(self):
        """Return positive microseconds after a measurement.

        Validates that getMicroseconds() returns a positive float
        after start() and stop() have been called.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        time.sleep(0.001)
        counter.stop()
        self.assertGreater(counter.getMicroseconds(), 0)

    def testGetMicrosecondsIsElapsedTimesOneMillion(self):
        """Compute microseconds as elapsed seconds times one million.

        Validates the conversion factor between elapsedTime() and
        getMicroseconds().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        counter.stop()
        self.assertAlmostEqual(
            counter.getMicroseconds(),
            counter.elapsedTime() * 1_000_000,
            places=9,
        )

    def testGetMillisecondsReturnsPositive(self):
        """Return positive milliseconds after a measurement.

        Validates that getMilliseconds() returns a positive float
        after a complete measurement cycle.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        time.sleep(0.001)
        counter.stop()
        self.assertGreater(counter.getMilliseconds(), 0)

    def testGetMillisecondsIsElapsedTimesOneThousand(self):
        """Compute milliseconds as elapsed seconds times one thousand.

        Validates the conversion factor between elapsedTime() and
        getMilliseconds().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        counter.stop()
        self.assertAlmostEqual(
            counter.getMilliseconds(),
            counter.elapsedTime() * 1_000,
            places=9,
        )

    def testGetSecondsMatchesElapsedTime(self):
        """Return the same value as elapsedTime from getSeconds.

        Validates that getSeconds() is an alias for elapsedTime()
        and produces the same result.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        counter.stop()
        self.assertEqual(counter.getSeconds(), counter.elapsedTime())

    def testGetMinutesIsElapsedTimeDividedBySixty(self):
        """Compute minutes as elapsed seconds divided by sixty.

        Validates the conversion factor between elapsedTime() and
        getMinutes().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        counter.stop()
        self.assertAlmostEqual(
            counter.getMinutes(),
            counter.elapsedTime() / 60,
            places=9,
        )

    def testGetMinutesIsLessThanGetSeconds(self):
        """Return a smaller value from getMinutes than getSeconds.

        Validates that minutes are always less than seconds for
        any positive elapsed duration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        time.sleep(0.01)
        counter.stop()
        self.assertLess(counter.getMinutes(), counter.getSeconds())

    # ------------------------------------------------ restart

    def testRestartReturnsSelf(self):
        """Return self from restart for method chaining.

        Validates that restart() returns the same PerformanceCounter
        instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        result = counter.restart()
        self.assertIs(result, counter)

    def testRestartAllowsNewMeasurement(self):
        """Allow a new measurement after restart.

        Validates that calling restart() followed by stop() produces
        a valid positive elapsed time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        time.sleep(0.01)
        counter.stop()
        counter.restart()
        time.sleep(0.005)
        counter.stop()
        self.assertGreater(counter.elapsedTime(), 0)

    def testRestartClearsPreviousElapsedTime(self):
        """Clear previous elapsed time on restart.

        Validates that after restart() and before stop(), calling
        elapsedTime() raises ValueError (counter not complete).

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        counter.stop()
        counter.restart()
        with self.assertRaises(ValueError):
            counter.elapsedTime()

    # ------------------------------------------------ context manager

    def testContextManagerStartsAndStopsCounter(self):
        """Start and stop the counter as a context manager.

        Validates that using PerformanceCounter as a context manager
        records a valid positive elapsed time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with PerformanceCounter() as counter:
            time.sleep(0.005)
        self.assertGreater(counter.elapsedTime(), 0)

    def testContextManagerReturnsSelf(self):
        """Return the counter instance from context manager __enter__.

        Validates that the variable bound via `with ... as x` is
        the same PerformanceCounter instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        with counter as ctx:
            pass
        self.assertIs(ctx, counter)

    def testContextManagerElapsedTimeIsFloat(self):
        """Return elapsed time as a float after context manager usage.

        Validates that elapsedTime() is a float after the context
        manager block completes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with PerformanceCounter() as counter:
            pass
        self.assertIsInstance(counter.elapsedTime(), float)

    def testContextManagerWithExceptionStillStops(self):
        """Stop the counter even when an exception occurs inside the block.

        Validates that __exit__ is called and stop() records a time
        even when the context body raises an exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        ValueError
            Raised by this helper to exercise the failure path.
        """
        counter = PerformanceCounter()
        try:
            with counter:
                error_msg = "test error"
                raise ValueError(error_msg)
        except ValueError:
            pass
        self.assertGreater(counter.elapsedTime(), 0)

class TestPerformanceCounterAsync(TestCase):
    """Unit tests for PerformanceCounter asynchronous interface."""

    # ------------------------------------------------ astart / astop

    async def testAstartReturnsSelf(self):
        """Return self from astart for method chaining.

        Validates that astart() returns the same PerformanceCounter
        instance when awaited.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        result = await counter.astart()
        self.assertIs(result, counter)

    async def testAstopReturnsSelf(self):
        """Return self from astop for method chaining.

        Validates that astop() returns the same PerformanceCounter
        instance after recording the elapsed time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        await counter.astart()
        result = await counter.astop()
        self.assertIs(result, counter)

    async def testAstartAndAstopProducePositiveElapsedTime(self):
        """Produce positive elapsed time after async start and stop.

        Validates that awaiting astart() and astop() results in a
        positive elapsed time value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        await counter.astart()
        await asyncio.sleep(0.01)
        await counter.astop()
        self.assertGreater(counter.elapsedTime(), 0)

    async def testAstartClearsPreviousMeasurement(self):
        """Clear the prior result when a new async measurement starts.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with patch(
            "orionis.support.performance.counter.time.perf_counter",
            side_effect=(1.0, 2.0, 3.0),
        ):
            counter = PerformanceCounter()
            await counter.astart()
            await counter.astop()
            await counter.astart()
            with self.assertRaises(ValueError):
                counter.elapsedTime()

    async def testAstopRaisesAfterSyncStart(self):
        """Raise RuntimeError when astop is called after sync start.

        Validates that mixing sync start() with async astop() raises
        a RuntimeError.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        counter.start()
        with self.assertRaises(RuntimeError):
            await counter.astop()

    # ------------------------------------------------ async unit conversions

    async def testAelapsedTimeMatchesSyncElapsedTime(self):
        """Return the same value from async and sync elapsed time.

        Validates that aelapsedTime() delegates to elapsedTime() and
        produces identical results.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        await counter.astart()
        await counter.astop()
        sync_val = counter.elapsedTime()
        async_val = await counter.aelapsedTime()
        self.assertEqual(sync_val, async_val)

    async def testAgetMicrosecondsMatchesSyncVersion(self):
        """Match async microseconds with sync microseconds.

        Validates that agetMicroseconds() returns the same value
        as getMicroseconds() after a measurement.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        await counter.astart()
        await counter.astop()
        self.assertAlmostEqual(
            await counter.agetMicroseconds(),
            counter.getMicroseconds(),
            places=9,
        )

    async def testAgetMillisecondsMatchesSyncVersion(self):
        """Match async milliseconds with sync milliseconds.

        Validates that agetMilliseconds() returns the same value
        as getMilliseconds() after a measurement.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        await counter.astart()
        await counter.astop()
        self.assertAlmostEqual(
            await counter.agetMilliseconds(),
            counter.getMilliseconds(),
            places=9,
        )

    async def testAgetSecondsMatchesSyncVersion(self):
        """Match async seconds with sync seconds.

        Validates that agetSeconds() returns the same value as
        getSeconds() after a measurement.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        await counter.astart()
        await counter.astop()
        self.assertEqual(
            await counter.agetSeconds(),
            counter.getSeconds(),
        )

    async def testAgetMinutesMatchesSyncVersion(self):
        """Match async minutes with sync minutes.

        Validates that agetMinutes() returns the same value as
        getMinutes() after a measurement.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        await counter.astart()
        await counter.astop()
        self.assertAlmostEqual(
            await counter.agetMinutes(),
            counter.getMinutes(),
            places=9,
        )

    # ------------------------------------------------ async restart

    async def testArestartReturnsSelf(self):
        """Return self from arestart for method chaining.

        Validates that arestart() returns the same PerformanceCounter
        instance when awaited.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        result = await counter.arestart()
        self.assertIs(result, counter)

    async def testArestartAllowsNewMeasurement(self):
        """Allow a new async measurement after arestart.

        Validates that calling arestart() followed by astop() produces
        a valid positive elapsed time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        await counter.astart()
        await asyncio.sleep(0.005)
        await counter.astop()
        await counter.arestart()
        await asyncio.sleep(0.005)
        await counter.astop()
        self.assertGreater(counter.elapsedTime(), 0)

    async def testArestartClearsPreviousElapsedTime(self):
        """Clear the previous elapsed time on async restart.

        Validates that after arestart() and before astop(), calling
        elapsedTime() raises ValueError.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        await counter.astart()
        await counter.astop()
        await counter.arestart()
        with self.assertRaises(ValueError):
            counter.elapsedTime()

    # ------------------------------------------------ async context manager

    async def testAsyncContextManagerRecordsElapsedTime(self):
        """Start and stop the counter via async context manager.

        Validates that using PerformanceCounter as an async context
        manager records a valid positive elapsed time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        async with PerformanceCounter() as counter:
            await asyncio.sleep(0.005)
        self.assertGreater(counter.elapsedTime(), 0)

    async def testAsyncContextManagerReturnsSelf(self):
        """Return the counter instance from async context manager __aenter__.

        Validates that the variable bound via `async with ... as x`
        is the same PerformanceCounter instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        async with counter as ctx:
            pass
        self.assertIs(ctx, counter)

    async def testAsyncContextManagerElapsedTimeIsFloat(self):
        """Return elapsed time as a float after async context manager.

        Validates that elapsedTime() is a float after the async
        context manager block completes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        async with PerformanceCounter() as counter:
            pass
        self.assertIsInstance(counter.elapsedTime(), float)

    async def testAsyncContextManagerWithExceptionStillStops(self):
        """Stop async counter even when an exception occurs inside block.

        Validates that __aexit__ is called and astop() records a time
        even when the async context body raises an exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.

        Raises
        ------
        ValueError
            Raised by this helper to exercise the failure path.
        """
        counter = PerformanceCounter()
        try:
            async with counter:
                error_msg = "async test error"
                raise ValueError(error_msg)
        except ValueError:
            pass
        self.assertGreater(counter.elapsedTime(), 0)

    # ------------------------------------------------ unit relationship

    async def testMicrosecondsGreaterThanMilliseconds(self):
        """Return more microseconds than milliseconds for the same interval.

        Validates the relative scale of unit conversions for any
        positive elapsed duration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        await counter.astart()
        await asyncio.sleep(0.01)
        await counter.astop()
        self.assertGreater(
            await counter.agetMicroseconds(),
            await counter.agetMilliseconds(),
        )

    async def testMillisecondsGreaterThanSeconds(self):
        """Return more milliseconds than seconds for the same interval.

        Validates the relative scale between millisecond and second
        conversions for any positive elapsed duration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        counter = PerformanceCounter()
        await counter.astart()
        await asyncio.sleep(0.01)
        await counter.astop()
        self.assertGreater(
            await counter.agetMilliseconds(),
            await counter.agetSeconds(),
        )
