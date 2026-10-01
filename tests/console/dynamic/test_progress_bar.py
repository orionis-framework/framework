from __future__ import annotations
import io
import sys
from unittest.mock import patch
from orionis.console.dynamic.contracts.progress_bar import IProgressBar
from orionis.console.dynamic.progress_bar import ProgressBar
from orionis.test import TestCase

class TestProgressBar(TestCase):

    def _make(self, total: int = 100, width: int = 50) -> ProgressBar:
        """
        Create a ProgressBar with stdout patched to suppress terminal output.

        Parameters
        ----------
        total : int, optional
            Maximum progress value. Default is 100.
        width : int, optional
            Width of the bar in characters. Default is 50.

        Returns
        -------
        ProgressBar
            A configured ProgressBar instance.
        """
        return ProgressBar(total=total, width=width)

    # ------------------------------------------------------------------ #
    #  Interface & instantiation                                         #
    # ------------------------------------------------------------------ #

    def testInheritsFromIProgressBar(self) -> None:
        """Verify that ProgressBar inherits from IProgressBar.

        Ensures the implementation follows the expected class hierarchy
        and satisfies the abstract interface contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(ProgressBar, IProgressBar))

    def testCanBeInstantiatedWithDefaults(self) -> None:
        """Verify that ProgressBar can be created with default arguments.

        Ensures the constructor completes without errors when no arguments
        are supplied, using total=100 and width=50.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb = ProgressBar()
        self.assertIsInstance(pb, ProgressBar)

    def testDefaultTotalAndWidth(self) -> None:
        """Verify the default values for total and bar_width after construction.

        Ensures total defaults to 100 and bar_width defaults to 50
        when no constructor arguments are provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make()
        self.assertEqual(pb.total, 100)
        self.assertEqual(pb.bar_width, 50)

    def testCustomTotalAndWidth(self) -> None:
        """Verify that custom total and width values are stored correctly.

        Ensures the constructor assigns the supplied arguments to the
        corresponding instance attributes without modification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make(total=200, width=30)
        self.assertEqual(pb.total, 200)
        self.assertEqual(pb.bar_width, 30)

    def testInitialProgressIsZero(self) -> None:
        """Verify that progress is initialised to zero on construction.

        Ensures that a freshly created ProgressBar always starts at 0
        regardless of the total value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make(total=50)
        self.assertEqual(pb.progress, 0)

    # start -------------------------------------------------------------- #

    def testStartResetsProgressToZero(self) -> None:
        """Verify that start() resets progress to zero.

        Ensures that even after advancing, calling start() brings
        the progress counter back to its initial value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make()
        pb.progress = 40
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb.start()
        self.assertEqual(pb.progress, 0)

    def testStartWritesToStdout(self) -> None:
        """Verify that start() writes the initial bar to stdout.

        Ensures that the visual representation is rendered when start
        is called, so the bar is visible from the very beginning.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            pb = self._make()
            pb.start()
        self.assertGreater(len(buf.getvalue()), 0)

    def testStartOutputContainsZeroPercent(self) -> None:
        """Verify that the output of start() shows 0% completion.

        Ensures the rendered bar reflects the reset state and displays
        zero percent progress to the user.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            pb = self._make()
            pb.start()
        self.assertIn("0%", buf.getvalue())

    # advance ------------------------------------------------------------ #

    def testAdvanceIncreasesByDefaultOne(self) -> None:
        """Verify that advance() with no argument increases progress by 1.

        Ensures the default increment of 1 is applied when advance is
        called without an explicit argument.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make()
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb.advance()
        self.assertEqual(pb.progress, 1)

    def testAdvanceIncreasesBySpecifiedAmount(self) -> None:
        """Verify that advance() increases progress by the given increment.

        Ensures the progress counter is updated correctly when a custom
        increment value is passed to the method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make(total=100)
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb.advance(10)
        self.assertEqual(pb.progress, 10)

    def testAdvanceDoesNotExceedTotal(self) -> None:
        """Verify that advance() caps progress at the total value.

        Ensures that passing an increment large enough to overshoot
        the total does not produce a progress value greater than total.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make(total=10)
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb.advance(999)
        self.assertEqual(pb.progress, 10)

    def testAdvanceMultipleTimesAccumulates(self) -> None:
        """Verify that successive advance() calls accumulate correctly.

        Ensures that multiple calls sum their increments as expected
        without any reset or loss between calls.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make(total=100)
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb.advance(10)
            pb.advance(20)
            pb.advance(5)
        self.assertEqual(pb.progress, 35)

    def testAdvanceWritesToStdout(self) -> None:
        """Verify that advance() renders output to stdout.

        Ensures the bar is redrawn each time advance is called so the
        user can observe the updated state.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            pb = self._make()
            pb.advance(50)
        self.assertGreater(len(buf.getvalue()), 0)

    def testAdvanceAtExactTotal(self) -> None:
        """Verify that advancing exactly to total sets progress to total.

        Ensures that hitting the upper boundary precisely is handled
        without clamping to an unexpected value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make(total=10)
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb.advance(10)
        self.assertEqual(pb.progress, 10)

    def testAdvanceFromNonZeroStartingPoint(self) -> None:
        """Verify that advance() correctly adds to a non-zero starting progress.

        Ensures the method does not reset or override the existing progress
        but adds the increment on top of it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make(total=100)
        pb.progress = 50
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb.advance(20)
        self.assertEqual(pb.progress, 70)

    # finish ------------------------------------------------------------- #

    def testFinishSetsProgressToTotal(self) -> None:
        """Verify that finish() sets progress to the total value.

        Ensures that calling finish from any intermediate state jumps
        the progress counter directly to 100%.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make(total=50)
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb.finish()
        self.assertEqual(pb.progress, 50)

    def testFinishWritesNewline(self) -> None:
        """Verify that finish() writes a newline character to stdout.

        Ensures the cursor is moved to a new line after the bar completes
        so subsequent console output starts on a fresh line.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            pb = self._make()
            pb.finish()
        self.assertIn("\n", buf.getvalue())

    def testFinishOutputContainsOneHundredPercent(self) -> None:
        """Verify that finish() renders 100% in the output.

        Ensures that the final state of the bar accurately reflects
        full completion to the user.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            pb = self._make()
            pb.finish()
        self.assertIn("100%", buf.getvalue())

    def testFinishFromMidpointSetsCompleted(self) -> None:
        """Verify that finish() completes the bar from any intermediate progress.

        Ensures that regardless of the current progress value, finish
        always results in total completion.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make(total=100)
        pb.progress = 37
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb.finish()
        self.assertEqual(pb.progress, 100)

    # ------------------------------------------------------------------ #
    #  Edge cases                                                        #
    # ------------------------------------------------------------------ #

    def testProgressBarWithTotalOne(self) -> None:
        """Verify that a ProgressBar with total=1 operates correctly.

        Ensures that a bar covering a single unit advances cleanly
        from 0 to 1 without overflow or division errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make(total=1)
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb.start()
            pb.advance()
            pb.finish()
        self.assertEqual(pb.progress, 1)

    def testProgressBarWithWidthOne(self) -> None:
        """Verify that a ProgressBar with width=1 renders without errors.

        Ensures that the minimum possible bar width does not cause any
        index or arithmetic errors when the bar is updated.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make(total=10, width=1)
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb.start()
            pb.advance(5)
            pb.finish()
        self.assertEqual(pb.progress, 10)

    def testAdvanceZeroDoesNotChangeProgress(self) -> None:
        """Verify that advancing by zero leaves progress unchanged.

        Ensures that a no-op increment does not alter the internal
        state or cause unintended side effects.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make()
        pb.progress = 25
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb.advance(0)
        self.assertEqual(pb.progress, 25)

    def testStartAfterFinishResetsBar(self) -> None:
        """Verify that start() resets the bar even after finish() was called.

        Ensures the bar can be fully reused by calling start() again
        after a completed cycle.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        pb = self._make(total=10)
        with patch.object(sys, "stdout", new_callable=io.StringIO):
            pb.finish()
            pb.start()
        self.assertEqual(pb.progress, 0)

    def testBarOutputContainsBrackets(self) -> None:
        """Verify that the rendered bar output is enclosed in brackets.

        Ensures the visual format follows the expected pattern of
        [filled_chars remaining_chars] percentage.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        buf = io.StringIO()
        with patch.object(sys, "stdout", buf):
            pb = self._make(total=10)
            pb.start()
        output = buf.getvalue()
        self.assertIn("[", output)
        self.assertIn("]", output)
