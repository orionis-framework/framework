import inspect

from orionis.background.contracts.task import IBackgroundTask
from orionis.background.task import BackgroundTask
from orionis.background.tasks import BackgroundTasks
from orionis.test import TestCase

# Methods every background task implementation must provide.
_ABSTRACT_METHODS: frozenset[str] = frozenset({"run"})

def parameter_names(owner: type, method: str) -> list[str]:
    """
    Return the parameter names declared by a method of a class.

    Parameters
    ----------
    owner : type
        Class owning the inspected method.
    method : str
        Name of the method to inspect.

    Returns
    -------
    list[str]
        Ordered parameter names of the method signature.
    """
    return list(inspect.signature(getattr(owner, method)).parameters)

class _IncompleteTask(IBackgroundTask):
    """Contract implementation that leaves the run method abstract."""

class _MinimalTask(IBackgroundTask):
    """Smallest possible implementation of the background task contract."""

    def __init__(self) -> None:
        """
        Initialise the execution log.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.executions: list[str] = []

    async def run(self) -> None:
        """
        Record a single execution of the task.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.executions.append("ran")

class TestBackgroundTaskContract(TestCase):
    """Validate the abstract interface of a background task."""

    def testDeclaresTheExpectedAbstractSurface(self) -> None:
        """
        Declare exactly the documented abstract methods.

        Validates that implementers know the complete set of methods they
        are required to provide.
        """
        self.assertEqual(IBackgroundTask.__abstractmethods__, _ABSTRACT_METHODS)

    def testDeclaresRunAsACoroutineMethod(self) -> None:
        """
        Declare the run method as a coroutine.

        Validates that callers can await the contract method without
        inspecting the concrete implementation.
        """
        self.assertTrue(inspect.iscoroutinefunction(IBackgroundTask.run))

    def testDeclaresEmptySlots(self) -> None:
        """
        Declare empty slots on the interface.

        Validates that implementations declaring slots do not gain an
        instance dictionary through the contract.
        """
        self.assertEqual(IBackgroundTask.__slots__, ())

    def testCannotBeInstantiatedDirectly(self) -> None:
        """
        Reject direct instantiation of the interface.

        Validates that the contract stays abstract and cannot be used as a
        concrete task by mistake.
        """
        with self.assertRaises(TypeError):
            IBackgroundTask()  # type: ignore[abstract]

    def testRejectsSubclassesThatDoNotImplementRun(self) -> None:
        """
        Reject subclasses leaving the run method unimplemented.

        Validates that the abstract machinery keeps incomplete task
        implementations out of the system.
        """
        with self.assertRaises(TypeError):
            _IncompleteTask()  # type: ignore[abstract]

    async def testAcceptsSubclassesImplementingRun(self) -> None:
        """
        Accept subclasses providing the run coroutine.

        Validates that implementing the single abstract method is enough
        to obtain a usable background task.
        """
        task = _MinimalTask()

        await task.run()
        self.assertEqual(task.executions, ["ran"])

    def testFrameworkImplementationsDeriveFromTheContract(self) -> None:
        """
        Derive the shipped task classes from the interface.

        Validates that both concrete classes are substitutable wherever
        the contract is required.
        """
        self.assertTrue(issubclass(BackgroundTask, IBackgroundTask))
        self.assertTrue(issubclass(BackgroundTasks, IBackgroundTask))

    def testImplementationsMirrorTheContractSignature(self) -> None:
        """
        Mirror the contract signature in the implementation.

        Validates that the shipped task exposes the run method with the
        parameters declared by the interface.
        """
        self.assertEqual(
            parameter_names(BackgroundTask, "run"),
            parameter_names(IBackgroundTask, "run"),
        )
