from __future__ import annotations
from dataclasses import fields, is_dataclass
from orionis.console.entities.scheduler_event import SchedulerEvent
from orionis.console.enums.events import SchedulerEvent as SchedulerEventEnum
from orionis.support.entities.base import BaseEntity
from orionis.test import TestCase

class TestSchedulerEventEntity(TestCase):

    # ------------------------------------------------------------------ #
    #  Inheritance & type                                                #
    # ------------------------------------------------------------------ #

    def testInheritsFromBaseEntity(self) -> None:
        """Verify that SchedulerEvent inherits from BaseEntity.

        Ensures the entity follows the expected class hierarchy so that
        shared helpers such as toDict are available.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(SchedulerEvent, BaseEntity))

    def testIsDataclass(self) -> None:
        """Verify that SchedulerEvent is a dataclass.

        Ensures the class is properly decorated with @dataclass for
        field introspection and equality semantics.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(is_dataclass(SchedulerEvent))

    # ------------------------------------------------------------------ #
    #  Construction — description mapping                                #
    # ------------------------------------------------------------------ #

    def testStartedCodeSetsCorrectDescription(self) -> None:
        """Verify that the STARTED code produces the expected description.

        Ensures __post_init__ maps SchedulerEvent.STARTED to the message
        'Scheduler started.'

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = SchedulerEvent(code=SchedulerEventEnum.STARTED)
        self.assertEqual(event.description, "Scheduler started.")

    def testShutdownCodeSetsCorrectDescription(self) -> None:
        """Verify that the SHUTDOWN code produces the expected description.

        Ensures __post_init__ maps SchedulerEvent.SHUTDOWN to the message
        'Scheduler shutdown.'

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = SchedulerEvent(code=SchedulerEventEnum.SHUTDOWN)
        self.assertEqual(event.description, "Scheduler shutdown.")

    def testResumedCodeSetsCorrectDescription(self) -> None:
        """Verify that the RESUMED code produces the expected description.

        Ensures __post_init__ maps SchedulerEvent.RESUMED to the message
        'Scheduler resumed.'

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = SchedulerEvent(code=SchedulerEventEnum.RESUMED)
        self.assertEqual(event.description, "Scheduler resumed.")

    def testPausedCodeSetsCorrectDescription(self) -> None:
        """Verify that the PAUSED code produces the expected description.

        Ensures __post_init__ maps SchedulerEvent.PAUSED to the message
        'Scheduler paused.'

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = SchedulerEvent(code=SchedulerEventEnum.PAUSED)
        self.assertEqual(event.description, "Scheduler paused.")

    def testUnknownCodeSetsDefaultDescription(self) -> None:
        """Verify that an unknown code produces the fallback description.

        Ensures __post_init__ falls back to 'Unknown Task Event.' when
        the code does not match any known SchedulerEventEnum value.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = SchedulerEvent(code=9999)
        self.assertEqual(event.description, "Unknown Task Event.")

    # ------------------------------------------------------------------ #
    #  Default field values                                              #
    # ------------------------------------------------------------------ #

    def testDefaultJobstore(self) -> None:
        """Verify that jobstore defaults to 'memory'.

        Ensures the jobstore field carries the expected default storage
        backend when not explicitly specified.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = SchedulerEvent(code=SchedulerEventEnum.STARTED)
        self.assertEqual(event.jobstore, "memory")

    def testCustomJobstore(self) -> None:
        """Verify that a custom jobstore value is stored correctly.

        Ensures the jobstore field accepts and retains any string value
        provided at construction time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = SchedulerEvent(code=SchedulerEventEnum.STARTED, jobstore="redis")
        self.assertEqual(event.jobstore, "redis")

    # ------------------------------------------------------------------ #
    #  Immutability (frozen dataclass via BaseEntity)                    #
    # ------------------------------------------------------------------ #

    def testCodeFieldIsStored(self) -> None:
        """Verify that the code field is accessible after construction.

        Ensures the integer event code is stored and retrievable as
        an attribute on the entity instance.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = SchedulerEvent(code=SchedulerEventEnum.PAUSED)
        self.assertEqual(event.code, SchedulerEventEnum.PAUSED)

    # ------------------------------------------------------------------ #
    #  toDict                                                            #
    # ------------------------------------------------------------------ #

    def testToDictContainsAllFields(self) -> None:
        """Verify that toDict exposes all declared dataclass fields.

        Ensures the serialisation helper includes code, description,
        and jobstore in the returned dictionary.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = SchedulerEvent(code=SchedulerEventEnum.STARTED)
        d = event.toDict()
        for f in fields(SchedulerEvent):
            self.assertIn(f.name, d)

    def testToDictDescriptionMatchesPostInit(self) -> None:
        """Verify that the description in toDict reflects the post_init mapping.

        Ensures the serialised description matches the value set during
        initialisation and not the empty default.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        event = SchedulerEvent(code=SchedulerEventEnum.SHUTDOWN)
        self.assertEqual(event.toDict()["description"], "Scheduler shutdown.")

    # ------------------------------------------------------------------ #
    #  Equality                                                          #
    # ------------------------------------------------------------------ #

    def testTwoInstancesWithSameCodeAreEqual(self) -> None:
        """Verify that two SchedulerEvent instances with the same code are equal.

        Ensures value-based equality works correctly for this entity so
        that duplicates can be detected.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = SchedulerEvent(code=SchedulerEventEnum.STARTED)
        b = SchedulerEvent(code=SchedulerEventEnum.STARTED)
        self.assertEqual(a, b)

    def testTwoInstancesWithDifferentCodesAreNotEqual(self) -> None:
        """Verify that SchedulerEvent instances with different codes are not equal.

        Ensures the code field participates in equality comparison.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = SchedulerEvent(code=SchedulerEventEnum.STARTED)
        b = SchedulerEvent(code=SchedulerEventEnum.SHUTDOWN)
        self.assertNotEqual(a, b)
