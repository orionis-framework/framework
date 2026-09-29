from __future__ import annotations
from dataclasses import fields, is_dataclass
from orionis.console.entities.task_event import TaskEvent
from orionis.console.enums.events import TaskEvent as TaskEventEnum
from orionis.support.entities.base import BaseEntity
from orionis.test import TestCase

class TestTaskEventEntity(TestCase):

    def _make(self, code: int = TaskEventEnum.EXECUTED, **kwargs) -> TaskEvent: # noqa: ANN003
        """
        Build a minimal valid TaskEvent instance.

        Parameters
        ----------
        code : int, optional
            Event code. Defaults to TaskEventEnum.EXECUTED.
        **kwargs
            Additional field overrides.

        Returns
        -------
        TaskEvent
            A configured TaskEvent ready for assertions.
        """
        defaults = {"code": code, "signature": "tasks.my_task"}
        defaults.update(kwargs)
        return TaskEvent(**defaults)

    # ------------------------------------------------------------------ #
    #  Inheritance & type                                                #
    # ------------------------------------------------------------------ #

    def testInheritsFromBaseEntity(self) -> None:
        """Verify that TaskEvent inherits from BaseEntity.

        Ensures the entity follows the expected class hierarchy and
        can use shared base functionality.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(TaskEvent, BaseEntity))

    def testIsDataclass(self) -> None:
        """Verify that TaskEvent is a dataclass.

        Ensures the class is decorated with @dataclass for field
        introspection and value equality.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(is_dataclass(TaskEvent))

    # ------------------------------------------------------------------ #
    #  Description mapping — all known codes                             #
    # ------------------------------------------------------------------ #

    def testAddedCodeSetsCorrectDescription(self) -> None:
        """Verify that ADDED code sets the description to 'Task Added'.

        Ensures __post_init__ correctly maps TaskEventEnum.ADDED.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make(code=TaskEventEnum.ADDED)
        self.assertEqual(event.description, "Task Added.")

    def testRemovedCodeSetsCorrectDescription(self) -> None:
        """Verify that REMOVED code sets the description to 'Task Removed'.

        Ensures __post_init__ correctly maps TaskEventEnum.REMOVED.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make(code=TaskEventEnum.REMOVED)
        self.assertEqual(event.description, "Task Removed.")

    def testModifiedCodeSetsCorrectDescription(self) -> None:
        """Verify that MODIFIED code sets the description to 'Task Modified'.

        Ensures __post_init__ correctly maps TaskEventEnum.MODIFIED.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make(code=TaskEventEnum.MODIFIED)
        self.assertEqual(event.description, "Task Modified.")

    def testExecutedCodeSetsCorrectDescription(self) -> None:
        """Verify that EXECUTED code sets the description to 'Task Executed'.

        Ensures __post_init__ correctly maps TaskEventEnum.EXECUTED.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make(code=TaskEventEnum.EXECUTED)
        self.assertEqual(event.description, "Task Executed.")

    def testErrorCodeSetsCorrectDescription(self) -> None:
        """Verify that ERROR code sets the description to 'Task Error'.

        Ensures __post_init__ correctly maps TaskEventEnum.ERROR.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make(code=TaskEventEnum.ERROR)
        self.assertEqual(event.description, "Task Error.")

    def testMissedCodeSetsCorrectDescription(self) -> None:
        """Verify that MISSED code sets the description to 'Task Missed'.

        Ensures __post_init__ correctly maps TaskEventEnum.MISSED.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make(code=TaskEventEnum.MISSED)
        self.assertEqual(event.description, "Task Missed.")

    def testSubmittedCodeSetsCorrectDescription(self) -> None:
        """Verify that SUBMITTED code sets the description to 'Task Submitted'.

        Ensures __post_init__ correctly maps TaskEventEnum.SUBMITTED.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make(code=TaskEventEnum.SUBMITTED)
        self.assertEqual(event.description, "Task Submitted.")

    def testMaxInstancesCodeSetsCorrectDescription(self) -> None:
        """Verify the description for the MAX_INSTANCES task event.

        Ensures __post_init__ correctly maps TaskEventEnum.MAX_INSTANCES.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make(code=TaskEventEnum.MAX_INSTANCES)
        self.assertEqual(event.description, "Task Reached Max Instances.")

    def testUnknownCodeSetsDefaultDescription(self) -> None:
        """Verify that an unknown code produces the fallback description.

        Ensures __post_init__ falls back to 'Unknown Task Event.' when
        the code does not match any known TaskEventEnum value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make(code=9999)
        self.assertEqual(event.description, "Unknown Task Event.")

    # ------------------------------------------------------------------ #
    #  Default field values                                              #
    # ------------------------------------------------------------------ #

    def testDefaultJobstore(self) -> None:
        """Verify that jobstore defaults to 'memory'.

        Ensures the storage backend field uses the expected default.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make()
        self.assertEqual(event.jobstore, "memory")

    def testDefaultOptionalFieldsAreNone(self) -> None:
        """Verify that all optional fields default to None.

        Ensures scheduled_run_times, scheduled_run_time, retval,
        exception, and traceback are None when not provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make()
        self.assertIsNone(event.scheduled_run_times)
        self.assertIsNone(event.scheduled_run_time)
        self.assertIsNone(event.retval)
        self.assertIsNone(event.exception)
        self.assertIsNone(event.traceback)

    # ------------------------------------------------------------------ #
    #  Custom field values                                               #
    # ------------------------------------------------------------------ #

    def testCustomSignatureIsStored(self) -> None:
        """Verify that a custom signature is stored correctly.

        Ensures the signature field retains the value supplied at
        construction without modification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make(signature="my.custom.task")
        self.assertEqual(event.signature, "my.custom.task")

    def testCustomRetvalIsStored(self) -> None:
        """Verify that a custom retval is stored correctly.

        Ensures the return-value field accepts any Python object and
        stores it as-is.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make(retval=42)
        self.assertEqual(event.retval, 42)

    def testCustomExceptionIsStored(self) -> None:
        """Verify that an exception object is stored on the entity.

        Ensures the exception field accepts an Exception instance and
        makes it accessible for downstream handling.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        exc = ValueError("oops")
        event = self._make(code=TaskEventEnum.ERROR, exception=exc)
        self.assertIs(event.exception, exc)

    def testCustomJobstore(self) -> None:
        """Verify that a custom jobstore string is accepted and stored.

        Ensures the field is not restricted to the default 'memory'
        backend.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make(jobstore="sqlalchemy")
        self.assertEqual(event.jobstore, "sqlalchemy")

    # ------------------------------------------------------------------ #
    #  toDict                                                            #
    # ------------------------------------------------------------------ #

    def testToDictContainsAllFields(self) -> None:
        """Verify that toDict exposes all declared dataclass fields.

        Ensures every field defined on TaskEvent is present in the
        serialised dictionary.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = self._make()
        d = event.toDict()
        for f in fields(TaskEvent):
            self.assertIn(f.name, d)

    # ------------------------------------------------------------------ #
    #  Equality                                                          #
    # ------------------------------------------------------------------ #

    def testTwoInstancesWithSameDataAreEqual(self) -> None:
        """Verify that two TaskEvent instances with identical data are equal.

        Ensures value-based equality works correctly so duplicates can
        be detected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = self._make(code=TaskEventEnum.EXECUTED, signature="t.task")
        b = self._make(code=TaskEventEnum.EXECUTED, signature="t.task")
        self.assertEqual(a, b)

    def testInstancesWithDifferentSignaturesAreNotEqual(self) -> None:
        """Verify that TaskEvent instances with different signatures differ.

        Ensures the signature field participates in equality comparison
        so two events for different tasks are not conflated.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = self._make(signature="task.a")
        b = self._make(signature="task.b")
        self.assertNotEqual(a, b)
