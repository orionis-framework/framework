from __future__ import annotations
import math
from unittest.mock import patch
from orionis.support.system.contracts.workers import IWorkers
from orionis.support.system.workers import Workers
from orionis.support.system import workers as workers_module
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Module path constant for patch targets
# ---------------------------------------------------------------------------

_MOD = "orionis.support.system.workers"

# ---------------------------------------------------------------------------
# Controlled hardware constants used across all test classes
# ---------------------------------------------------------------------------

_CPU_COUNT = 4
_RAM_GB = 8.0
_RAM_BYTES = int(_RAM_GB * (1 << 30))

class TestCpuCountDetection(TestCase):
    def testUsesProcessCpuCountWhenAvailable(self) -> None:
        """Prefer the CPU count available to the current process.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with (
            patch.object(workers_module.os, "process_cpu_count", return_value=2),
            patch.object(workers_module.os, "cpu_count", return_value=8) as cpu_count,
        ):
            self.assertEqual(workers_module._get_cpu_count(), 2)
        cpu_count.assert_not_called()

    def testFallsBackToSystemCpuCountWhenProcessCountIsUnknown(self) -> None:
        """Use the system CPU count when the process count is unavailable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with (
            patch.object(workers_module.os, "process_cpu_count", return_value=None),
            patch.object(workers_module.os, "cpu_count", return_value=8),
        ):
            self.assertEqual(workers_module._get_cpu_count(), 8)

    def testFallsBackToOneWhenCpuCountsAreUnknown(self) -> None:
        """Keep the recommended CPU count positive when both lookups fail.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with (
            patch.object(workers_module.os, "process_cpu_count", return_value=None),
            patch.object(workers_module.os, "cpu_count", return_value=None),
        ):
            self.assertEqual(workers_module._get_cpu_count(), 1)

# ---------------------------------------------------------------------------
# TestWorkersInterface
# ---------------------------------------------------------------------------

class TestWorkersInterface(TestCase):
    def testImplementsIWorkers(self) -> None:
        """Verify Workers is a subclass of the IWorkers contract.

        Validates that the Workers class satisfies the abstract base
        class declared by IWorkers without requiring instantiation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(Workers, IWorkers))

    def testCanBeInstantiated(self) -> None:
        """Verify Workers can be instantiated without arguments.

        Validates that calling Workers() succeeds and produces a
        non-None object.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        instance = Workers()
        self.assertIsNotNone(instance)

    def testInstanceIsIWorkers(self) -> None:
        """Verify a Workers instance is recognised as IWorkers.

        Validates isinstance check against the abstract base class
        passes for a concrete Workers object.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(Workers(), IWorkers)

    def testHasCalculateMethod(self) -> None:
        """Verify the calculate classmethod exists and is callable.

        Validates that the Workers class exposes a public callable
        named ``calculate`` as required by the interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(callable(getattr(Workers, "calculate", None)))

    def testHasSetRamPerWorkerMethod(self) -> None:
        """Verify the setRamPerWorker classmethod exists and is callable.

        Validates that the Workers class exposes a public callable
        named ``setRamPerWorker`` as required by the interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(callable(getattr(Workers, "setRamPerWorker", None)))

# ---------------------------------------------------------------------------
# TestWorkersDefaultState
# ---------------------------------------------------------------------------

class TestWorkersDefaultState(TestCase):
    def setUp(self) -> None:
        """Save the class-level RAM allocation before each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._original_ram = Workers._ram_per_worker_bytes

    def tearDown(self) -> None:
        """Restore the class-level RAM allocation after each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        Workers._ram_per_worker_bytes = self._original_ram

    def testDefaultRamPerWorkerIsHalfGb(self) -> None:
        """Confirm the default RAM budget is stored in bytes.

        Validates the default 0.5 GB budget without converting it at
        calculation time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Workers._ram_per_worker_bytes, 1 << 29)

    def testRamPerWorkerIsStoredAsIntegerBytes(self) -> None:
        """Confirm the RAM-per-worker class variable is an integer byte count.

        Validates that the calculation uses an integer budget.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(Workers._ram_per_worker_bytes, int)

# ---------------------------------------------------------------------------
# TestWorkersSetRamPerWorker
# ---------------------------------------------------------------------------

class TestWorkersSetRamPerWorker(TestCase):
    def setUp(self) -> None:
        """Save the class-level RAM allocation before each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._original_ram = Workers._ram_per_worker_bytes

    def tearDown(self) -> None:
        """Restore the class-level RAM allocation after each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        Workers._ram_per_worker_bytes = self._original_ram

    def testSetRamPerWorkerUpdatesClassVariable(self) -> None:
        """Update the class-level RAM-per-worker via setRamPerWorker.

        Validates that the supplied value is stored as
        Workers._ram_per_worker_bytes immediately after the call.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(2.0)
        self.assertEqual(Workers._ram_per_worker_bytes, 2 << 30)

    def testSetRamPerWorkerOverridesPreviousValue(self) -> None:
        """Replace the previously stored RAM-per-worker with a new value.

        Validates that successive calls each overwrite the prior value
        without any accumulation side-effect.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(1.0)
        Workers.setRamPerWorker(3.5)
        self.assertEqual(Workers._ram_per_worker_bytes, int(3.5 * (1 << 30)))

    def testSetRamPerWorkerReturnsNone(self) -> None:
        """Return None from setRamPerWorker.

        Validates that the method produces no return value, in
        compliance with the IWorkers contract signature.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = Workers.setRamPerWorker(1.0)
        self.assertIsNone(result)

    def testSetRamPerWorkerAcceptsLargeValue(self) -> None:
        """Accept a large RAM-per-worker value without error.

        Validates that the byte budget is calculated when configured.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(512.0)
        self.assertEqual(Workers._ram_per_worker_bytes, 512 << 30)

    def testSetRamPerWorkerAcceptsSmallPositiveValue(self) -> None:
        """Accept a small positive RAM-per-worker value without error.

        Validates that fractional GB are converted to whole bytes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(0.001)
        self.assertEqual(
            Workers._ram_per_worker_bytes,
            int(0.001 * (1 << 30)),
        )

    def testSetRamPerWorkerRejectsInvalidBudgets(self) -> None:
        """Reject budgets that cannot describe a positive finite size.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for invalid_budget in (0.0, -1.0, math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError):
                Workers.setRamPerWorker(invalid_budget)

    def testSetRamPerWorkerRejectsBudgetsSmallerThanOneByte(self) -> None:
        """Reject a positive GB value that truncates to zero bytes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Workers.setRamPerWorker(1e-12)

# ---------------------------------------------------------------------------
# TestWorkersCalculate
# ---------------------------------------------------------------------------

class TestWorkersCalculate(TestCase):
    def setUp(self) -> None:
        """Save the class-level RAM allocation before each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._original_ram = Workers._ram_per_worker_bytes

    def tearDown(self) -> None:
        """Restore the class-level RAM allocation after each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        Workers._ram_per_worker_bytes = self._original_ram

    def testCalculateReturnsCpuBoundResult(self) -> None:
        """Return the CPU count when RAM capacity exceeds CPU capacity.

        Validates that calculate() returns _CPU_COUNT (4) when
        floor(RAM / ram_per_worker) is larger than the CPU count.
        With 8 GB RAM and 0.5 GB per worker the RAM allows 16 workers,
        so the CPU count of 4 is the binding constraint.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(0.5)
        with (
            patch(f"{_MOD}._CPU_COUNT", _CPU_COUNT),
            patch(f"{_MOD}._RAM_TOTAL_BYTES", _RAM_BYTES),
        ):
            result = Workers.calculate()
        # floor(8 / 0.5) = 16 → min(4, 16) = 4
        self.assertEqual(result, 4)

    def testCalculateReturnsRamBoundResult(self) -> None:
        """Return the RAM-derived count when memory is the bottleneck.

        Validates that calculate() returns the floor-divided RAM count
        when it is lower than the available CPU cores.
        With 8 GB RAM and 4 GB per worker only 2 workers fit in RAM.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(4.0)
        with (
            patch(f"{_MOD}._CPU_COUNT", _CPU_COUNT),
            patch(f"{_MOD}._RAM_TOTAL_BYTES", _RAM_BYTES),
        ):
            result = Workers.calculate()
        # floor(8 / 4) = 2 → min(4, 2) = 2
        self.assertEqual(result, 2)

    def testCalculateReturnsTieBreaker(self) -> None:
        """Return the shared value when CPU and RAM capacities are equal.

        Validates that when both constraints yield the same count
        the result equals that count (min(n, n) == n).
        With 8 GB RAM and 2 GB per worker, floor(8/2)=4 == CPU count.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(2.0)
        with (
            patch(f"{_MOD}._CPU_COUNT", _CPU_COUNT),
            patch(f"{_MOD}._RAM_TOTAL_BYTES", _RAM_BYTES),
        ):
            result = Workers.calculate()
        self.assertEqual(result, 4)

    def testCalculateFloorsDivisionResult(self) -> None:
        """Apply integer floor division when RAM does not divide evenly.

        Validates that calculate() never rounds up the RAM-derived
        worker count when the division is not exact.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(3.0)
        with (
            patch(f"{_MOD}._CPU_COUNT", _CPU_COUNT),
            patch(f"{_MOD}._RAM_TOTAL_BYTES", _RAM_BYTES),
        ):
            result = Workers.calculate()
        expected_ram = math.floor(_RAM_GB / 3.0)
        self.assertEqual(result, min(_CPU_COUNT, expected_ram))

    def testCalculateReturnsInteger(self) -> None:
        """Return an integer from calculate.

        Validates that the return type is always int, not float or
        any other numeric type, regardless of the inputs.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(0.5)
        with (
            patch(f"{_MOD}._CPU_COUNT", _CPU_COUNT),
            patch(f"{_MOD}._RAM_TOTAL_BYTES", _RAM_BYTES),
        ):
            result = Workers.calculate()
        self.assertIsInstance(result, int)

    def testCalculateReflectsSetRamPerWorker(self) -> None:
        """Reflect the updated RAM allocation in the next calculate call.

        Validates that setRamPerWorker before calculate uses the new
        value rather than the previously stored one.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with (
            patch(f"{_MOD}._CPU_COUNT", _CPU_COUNT),
            patch(f"{_MOD}._RAM_TOTAL_BYTES", _RAM_BYTES),
        ):
            Workers.setRamPerWorker(0.5)
            first = Workers.calculate()
            Workers.setRamPerWorker(8.0)
            second = Workers.calculate()
        self.assertEqual(first, 4)
        self.assertEqual(second, 1)

    def testCalculateWithSingleCpuReturnsOne(self) -> None:
        """Return one when only a single CPU core is available.

        Validates that a single-CPU machine never yields more than one
        recommended worker regardless of available RAM.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(0.5)
        with (
            patch(f"{_MOD}._CPU_COUNT", 1),
            patch(f"{_MOD}._RAM_TOTAL_BYTES", _RAM_BYTES),
        ):
            result = Workers.calculate()
        self.assertEqual(result, 1)

    def testCalculateWithSmallRamPerWorkerIsCpuBound(self) -> None:
        """Cap the result at CPU count when abundant RAM is available.

        Validates that extremely small per-worker RAM allocation does
        not produce a result greater than the number of CPU cores.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(0.1)
        with (
            patch(f"{_MOD}._CPU_COUNT", _CPU_COUNT),
            patch(f"{_MOD}._RAM_TOTAL_BYTES", _RAM_BYTES),
        ):
            result = Workers.calculate()
        # floor(8 / 0.1) = 80 → min(4, 80) = 4
        self.assertEqual(result, _CPU_COUNT)

    def testCalculateConsistencyOverMultipleCalls(self) -> None:
        """Return the same value on repeated calls without side effects.

        Validates that calculate() is deterministic: identical inputs
        always produce identical output across successive invocations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(1.0)
        with (
            patch(f"{_MOD}._CPU_COUNT", _CPU_COUNT),
            patch(f"{_MOD}._RAM_TOTAL_BYTES", _RAM_BYTES),
        ):
            first = Workers.calculate()
            second = Workers.calculate()
        self.assertEqual(first, second)

    def testCalculateWithOneByteTotalRamReturnsOne(self) -> None:
        """Return at least one when total RAM is one byte.

        Validates that floor(1 / ram_per_worker_bytes) == 0 triggers
        the ``or 1`` fallback, ensuring the result is never less than
        one for a valid positive configuration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(0.5)
        with (
            patch(f"{_MOD}._CPU_COUNT", _CPU_COUNT),
            patch(f"{_MOD}._RAM_TOTAL_BYTES", 1),
        ):
            result = Workers.calculate()
        # 1 // ram_bytes == 0 → min(4, 0) == 0 → 0 or 1 == 1
        self.assertEqual(result, 1)

    def testCalculateWithLargeRamPerWorkerReturnsOne(self) -> None:
        """Return one when per-worker RAM exceeds total available memory.

        Validates that when floor(total / per_worker) == 0 the
        ``or 1`` guard keeps the result at the minimum of 1.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(100.0)
        with (
            patch(f"{_MOD}._CPU_COUNT", _CPU_COUNT),
            patch(f"{_MOD}._RAM_TOTAL_BYTES", _RAM_BYTES),
        ):
            result = Workers.calculate()
        # floor(8G / 100G) = 0 → min(4, 0) = 0 → 0 or 1 = 1
        self.assertEqual(result, 1)

# ---------------------------------------------------------------------------
# TestWorkersEdgeCases
# ---------------------------------------------------------------------------

class TestWorkersEdgeCases(TestCase):
    def setUp(self) -> None:
        """Save the class-level RAM allocation before each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self._original_ram = Workers._ram_per_worker_bytes

    def tearDown(self) -> None:
        """Restore the class-level RAM allocation after each test.

        Returns
        -------
        None
            Completes the operation described above.
        """
        Workers._ram_per_worker_bytes = self._original_ram

    def testSetRamPerWorkerRejectsZero(self) -> None:
        """Raise ValueError when ram_per_worker is zero.

        Validates invalid budgets are rejected before calculate() uses
        them.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Workers.setRamPerWorker(0.0)

    def testSetRamPerWorkerRejectsNegative(self) -> None:
        """Raise ValueError when ram_per_worker is negative.

        Validates that calculate() cannot return a negative worker
        count from an invalid memory budget.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(ValueError):
            Workers.setRamPerWorker(-1.0)

    def testSetRamPerWorkerRejectsInvalidValueWithoutChangingBudget(self) -> None:
        """Preserve the active budget when a new value is invalid.

        Validates that setter validation completes before updating the
        class-level byte count.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        Workers.setRamPerWorker(2.0)
        active_budget = Workers._ram_per_worker_bytes
        with self.assertRaises(ValueError):
            Workers.setRamPerWorker(0.0)
        self.assertEqual(Workers._ram_per_worker_bytes, active_budget)

    def testCalculateWithMinimalCpuAndExactRam(self) -> None:
        """Return one for a single CPU with exactly one worker's worth of RAM.

        Validates that the minimum valid configuration (1 CPU, exactly
        ram_per_worker bytes of total RAM) yields a result of exactly one.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        per_worker_bytes = int(0.5 * (1 << 30))
        Workers.setRamPerWorker(0.5)
        with (
            patch(f"{_MOD}._CPU_COUNT", 1),
            patch(f"{_MOD}._RAM_TOTAL_BYTES", per_worker_bytes),
        ):
            result = Workers.calculate()
        self.assertEqual(result, 1)
