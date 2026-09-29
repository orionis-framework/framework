from __future__ import annotations
from dataclasses import fields, is_dataclass
from orionis.console.entities.task import Task
from orionis.support.entities.base import BaseEntity
from orionis.test import TestCase

class TestTaskEntity(TestCase):

    def _make(self, **kwargs: object) -> Task:
        """
        Build a minimal valid Task instance.

        Parameters
        ----------
        **kwargs
            Field overrides applied on top of defaults.

        Returns
        -------
        Task
            A configured Task instance ready for assertions.
        """
        defaults = {"signature": "tasks.my_job"}
        defaults.update(kwargs)
        return Task(**defaults)

    # ------------------------------------------------------------------ #
    #  Inheritance & type                                                #
    # ------------------------------------------------------------------ #

    def testInheritsFromBaseEntity(self) -> None:
        """Verify that Task inherits from BaseEntity.

        Ensures the entity participates in the shared class hierarchy
        and gains helpers such as toDict.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(Task, BaseEntity))

    def testIsDataclass(self) -> None:
        """Verify that Task is a dataclass.

        Ensures the class is decorated with @dataclass so that field
        introspection and value equality work as expected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(is_dataclass(Task))

    # ------------------------------------------------------------------ #
    #  Construction — normal cases                                       #
    # ------------------------------------------------------------------ #

    def testCanBeInstantiatedWithOnlySignature(self) -> None:
        """Verify that Task can be created with only the signature field.

        Ensures instantiation succeeds when only the required signature
        is provided and all optional fields use their defaults.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make()
        self.assertIsInstance(task, Task)

    def testSignatureIsStored(self) -> None:
        """Verify that the signature value is accessible after construction.

        Ensures the unique identifier field retains the supplied string
        without modification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make(signature="jobs.send_email")
        self.assertEqual(task.signature, "jobs.send_email")

    # ------------------------------------------------------------------ #
    #  Default field values                                              #
    # ------------------------------------------------------------------ #

    def testDefaultArgsIsEmptyList(self) -> None:
        """Verify that args defaults to an empty list.

        Ensures the default_factory produces a fresh empty list when
        no args are provided, not None.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make()
        self.assertIsInstance(task.args, list)
        self.assertEqual(len(task.args), 0)

    def testDefaultArgsDontShareState(self) -> None:
        """Verify that two tasks with default args have independent lists.

        Ensures the default_factory creates a new list per instance so
        mutations on one task do not affect another.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = self._make()
        b = self._make()
        a.args.append("x")
        self.assertEqual(len(b.args), 0)

    def testDefaultListenersIsEmptyList(self) -> None:
        """Verify that listeners defaults to an empty list.

        Ensures the default_factory produces a fresh empty list when no
        listeners are provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make()
        self.assertIsInstance(task.listeners, list)
        self.assertEqual(len(task.listeners), 0)

    def testDefaultOptionalFieldsAreNone(self) -> None:
        """Verify that all nullable optional fields default to None.

        Ensures purpose, random_delay, start_date, end_date, trigger,
        details, and misfire_grace_time are None on a fresh instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make()
        self.assertIsNone(task.purpose)
        self.assertIsNone(task.random_delay)
        self.assertIsNone(task.start_date)
        self.assertIsNone(task.end_date)
        self.assertIsNone(task.trigger)
        self.assertIsNone(task.details)
        self.assertIsNone(task.misfire_grace_time)

    def testDefaultMaxInstances(self) -> None:
        """Verify that max_instances defaults to 1.

        Ensures the concurrency limit is conservatively set to a single
        instance unless explicitly overridden.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make()
        self.assertEqual(task.max_instances, 1)

    def testDefaultCoalesceIsTrue(self) -> None:
        """Verify that coalesce defaults to True.

        Ensures missed runs are coalesced into a single execution by
        default to prevent job storms.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make()
        self.assertTrue(task.coalesce)

    # ------------------------------------------------------------------ #
    #  Construction — custom values                                      #
    # ------------------------------------------------------------------ #

    def testCustomArgsAreStored(self) -> None:
        """Verify that a custom args list is stored correctly.

        Ensures the supplied list is retained on the instance and
        accessible as the args attribute.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make(args=["--verbose", "--dry-run"])
        self.assertEqual(task.args, ["--verbose", "--dry-run"])

    def testCustomPurposeIsStored(self) -> None:
        """Verify that a custom purpose string is stored correctly.

        Ensures the descriptive purpose field accepts and retains any
        string value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make(purpose="Send nightly report")
        self.assertEqual(task.purpose, "Send nightly report")

    def testCustomMaxInstancesIsStored(self) -> None:
        """Verify that a custom max_instances value is stored correctly.

        Ensures the integer concurrency cap is accepted without coercion
        or validation at the entity level.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make(max_instances=5)
        self.assertEqual(task.max_instances, 5)

    def testCustomCoalesceCanBeDisabled(self) -> None:
        """Verify that coalesce can be set to False.

        Ensures the boolean field accepts and stores False, enabling
        multiple missed executions to run individually.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make(coalesce=False)
        self.assertFalse(task.coalesce)

    def testCustomRandomDelay(self) -> None:
        """Verify that random_delay accepts an integer value.

        Ensures the optional jitter field stores an integer delay in
        seconds as provided.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make(random_delay=30)
        self.assertEqual(task.random_delay, 30)

    def testCustomDetailsIsStored(self) -> None:
        """Verify that the details field stores a custom string.

        Ensures additional metadata can be attached to a task without
        any transformation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make(details="runs on weekdays only")
        self.assertEqual(task.details, "runs on weekdays only")

    def testListenerIsStored(self) -> None:
        """Verify that a callable listener is stored in the listeners list.

        Ensures the default_factory list can hold callable objects and
        that they are accessible after construction.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        listener = lambda _event: None  # noqa: E731
        task = self._make(listeners=[listener])
        self.assertIn(listener, task.listeners)

    # ------------------------------------------------------------------ #
    #  toDict                                                            #
    # ------------------------------------------------------------------ #

    def testToDictContainsAllFields(self) -> None:
        """Verify that toDict exposes all declared dataclass fields.

        Ensures every field defined on Task appears in the serialised
        dictionary returned by the base helper.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make()
        d = task.toDict()
        for f in fields(Task):
            self.assertIn(f.name, d)

    def testToDictSignatureValue(self) -> None:
        """Verify that toDict correctly serialises the signature field.

        Ensures the string value is preserved verbatim in the output
        dictionary.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        task = self._make(signature="my.task")
        self.assertEqual(task.toDict()["signature"], "my.task")

    # ------------------------------------------------------------------ #
    #  Equality                                                          #
    # ------------------------------------------------------------------ #

    def testTwoInstancesWithSameDataAreEqual(self) -> None:
        """Verify that two Task instances with identical data compare equal.

        Ensures the dataclass equality mechanism works so that duplicate
        tasks can be detected by value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = self._make(signature="t.job")
        b = self._make(signature="t.job")
        self.assertEqual(a, b)

    def testInstancesWithDifferentSignaturesAreNotEqual(self) -> None:
        """Verify that Task instances with different signatures differ.

        Ensures the signature field participates in equality comparison
        so that distinct tasks are not conflated.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = self._make(signature="job.a")
        b = self._make(signature="job.b")
        self.assertNotEqual(a, b)
