from __future__ import annotations
import inspect
from unittest.mock import Mock
from orionis.console.base.contracts.scheduler import IBaseScheduler
from orionis.console.base.scheduler import BaseScheduler
from orionis.test import TestCase

class TestBaseScheduler(TestCase):

    def setUp(self) -> None:
        """Set up test fixtures.

        Creates a BaseScheduler instance and mock objects needed for testing.

        Returns
        -------
        None
            Completes the operation described above.
        """
        self.scheduler = BaseScheduler()
        self.mock_schedule = Mock()
        self.mock_event = Mock()

    def testInheritsFromIBaseScheduler(self) -> None:
        """Verify that BaseScheduler inherits from IBaseScheduler.

        Ensures that the base implementation properly implements the
        abstract interface and follows the inheritance hierarchy.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(BaseScheduler, IBaseScheduler))
        self.assertIsInstance(self.scheduler, IBaseScheduler)

    def testCanBeInstantiated(self) -> None:
        """Verify that BaseScheduler can be instantiated.

        Tests that the base scheduler implementation can be created
        without raising any exceptions, unlike the abstract interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        scheduler = BaseScheduler()
        self.assertIsInstance(scheduler, BaseScheduler)
        self.assertIsInstance(scheduler, IBaseScheduler)

    def testHasAllRequiredMethods(self) -> None:
        """Verify that BaseScheduler implements all required methods.

        Checks that all abstract methods from IBaseScheduler are implemented
        in the BaseScheduler class.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Check that all required methods exist
        self.assertTrue(hasattr(self.scheduler, "tasks"))
        self.assertTrue(hasattr(self.scheduler, "onStarted"))
        self.assertTrue(hasattr(self.scheduler, "onPaused"))
        self.assertTrue(hasattr(self.scheduler, "onResumed"))
        self.assertTrue(hasattr(self.scheduler, "onShutdown"))

    def testAllMethodsAreCallable(self) -> None:
        """Verify that all implemented methods are callable.

        Ensures that the BaseScheduler properly implements all methods
        as callable functions.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(callable(self.scheduler.tasks))
        self.assertTrue(callable(self.scheduler.onStarted))
        self.assertTrue(callable(self.scheduler.onPaused))
        self.assertTrue(callable(self.scheduler.onResumed))
        self.assertTrue(callable(self.scheduler.onShutdown))

    def testAllMethodsAreAsync(self) -> None:
        """Verify that all methods are asynchronous.

        Checks that all implemented methods are coroutine functions,
        matching the interface requirements.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(inspect.iscoroutinefunction(self.scheduler.tasks))
        self.assertTrue(inspect.iscoroutinefunction(self.scheduler.onStarted))
        self.assertTrue(inspect.iscoroutinefunction(self.scheduler.onPaused))
        self.assertTrue(inspect.iscoroutinefunction(self.scheduler.onResumed))
        self.assertTrue(inspect.iscoroutinefunction(self.scheduler.onShutdown))

    async def testTasksMethodRaisesNotImplementedError(self) -> None:
        """Verify that tasks method raises NotImplementedError.

        Tests that the base implementation's tasks method properly raises
        NotImplementedError, forcing subclasses to implement it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(NotImplementedError) as context:
            await self.scheduler.tasks(self.mock_schedule)
        error_message = str(context.exception)
        self.assertIn("Subclasses must implement the 'tasks' method", error_message)

    async def testOnStartedMethodExecutesWithoutError(self) -> None:
        """Verify that onStarted method executes without raising exceptions.

        Tests that the base implementation of onStarted completes successfully
        and doesn't raise any errors when called.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.scheduler.onStarted(self.mock_event)

    async def testOnPausedMethodExecutesWithoutError(self) -> None:
        """Verify that onPaused method executes without raising exceptions.

        Tests that the base implementation of onPaused completes successfully
        and doesn't raise any errors when called.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.scheduler.onPaused(self.mock_event)

    async def testOnResumedMethodExecutesWithoutError(self) -> None:
        """Verify that onResumed method executes without raising exceptions.

        Tests that the base implementation of onResumed completes successfully
        and doesn't raise any errors when called.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.scheduler.onResumed(self.mock_event)

    async def testOnShutdownMethodExecutesWithoutError(self) -> None:
        """Verify that onShutdown method executes without raising exceptions.

        Tests that the base implementation of onShutdown completes successfully
        and doesn't raise any errors when called.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        await self.scheduler.onShutdown(self.mock_event)

    async def testEventMethodsReturnNone(self) -> None:
        """Verify that event handler methods return None.

        Tests that all event handler methods properly return None as specified
        in their type annotations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result_started = await self.scheduler.onStarted(self.mock_event)
        result_paused = await self.scheduler.onPaused(self.mock_event)
        result_resumed = await self.scheduler.onResumed(self.mock_event)
        result_shutdown = await self.scheduler.onShutdown(self.mock_event)

        self.assertIsNone(result_started)
        self.assertIsNone(result_paused)
        self.assertIsNone(result_resumed)
        self.assertIsNone(result_shutdown)

    def testMethodSignaturesMatchInterface(self) -> None:
        """Verify that method signatures match the interface definition.

        Ensures that all implemented methods have the same signatures as
        defined in the IBaseScheduler interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Get signatures from both interface and implementation
        interface_tasks_sig = inspect.signature(IBaseScheduler.tasks)
        impl_tasks_sig = inspect.signature(BaseScheduler.tasks)

        interface_on_started_sig = inspect.signature(IBaseScheduler.onStarted)
        impl_on_started_sig = inspect.signature(BaseScheduler.onStarted)

        # Compare parameter counts (excluding 'self')
        self.assertEqual(
            len(interface_tasks_sig.parameters),
            len(impl_tasks_sig.parameters),
        )
        self.assertEqual(
            len(interface_on_started_sig.parameters),
            len(impl_on_started_sig.parameters),
        )

    async def testEventMethodsAcceptAnyEventType(self) -> None:
        """Verify that event methods accept various event types.

        Tests that event handler methods can handle different types of
        event objects without raising type-related errors.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Test with different event object types
        mock_events = [
            Mock(),
            Mock(code=1, description="test"),
            Mock(code=2, jobstore="memory"),
            None,  # Edge case: None event
        ]

        for event in mock_events:
            await self.scheduler.onStarted(event)
            await self.scheduler.onPaused(event)
            await self.scheduler.onResumed(event)
            await self.scheduler.onShutdown(event)

    async def testTasksMethodValidatesScheduleParameter(self) -> None:
        """Verify that tasks method handles invalid schedule parameter.

        Tests that the tasks method behaves properly when called with
        invalid or None schedule objects.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Test with None schedule
        with self.assertRaises(NotImplementedError):
            await self.scheduler.tasks(None)

        # Test with mock schedule - should still raise NotImplementedError
        # since the base implementation doesn't do any actual work
        with self.assertRaises(NotImplementedError):
            await self.scheduler.tasks(self.mock_schedule)

    def testClassIsNotAbstract(self) -> None:
        """Verify that BaseScheduler is not an abstract class.

        Ensures that BaseScheduler can be instantiated and doesn't have
        any remaining abstract methods.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertFalse(inspect.isabstract(BaseScheduler))

    def testMethodsHaveProperDocstrings(self) -> None:
        """Verify that implemented methods have proper documentation.

        Checks that all methods include proper docstrings following
        the project's documentation standards.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        # Check that methods have non-empty docstrings
        self.assertIsNotNone(BaseScheduler.tasks.__doc__)
        self.assertIsNotNone(BaseScheduler.onStarted.__doc__)
        self.assertIsNotNone(BaseScheduler.onPaused.__doc__)
        self.assertIsNotNone(BaseScheduler.onResumed.__doc__)
        self.assertIsNotNone(BaseScheduler.onShutdown.__doc__)

        # Check that docstrings are not just whitespace
        self.assertTrue(BaseScheduler.tasks.__doc__.strip())
        self.assertTrue(BaseScheduler.onStarted.__doc__.strip())
        self.assertTrue(BaseScheduler.onPaused.__doc__.strip())
        self.assertTrue(BaseScheduler.onResumed.__doc__.strip())
        self.assertTrue(BaseScheduler.onShutdown.__doc__.strip())
