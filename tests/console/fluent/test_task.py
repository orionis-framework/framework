from datetime import datetime
from unittest.mock import MagicMock, patch
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from orionis.test import TestCase
from orionis.console.fluent.task import Task
from orionis.console.base.listener import BaseTaskListener
from orionis.console.entities.task import Task as TaskEntity
from orionis.console.enums.events import TaskEvent

def _make_task(signature="test:sig", args=None, purpose=None):
    """Create a Task instance with minimal required arguments."""
    return Task(signature=signature, args=args, purpose=purpose)

class _ConcreteListener(BaseTaskListener):
    """Minimal concrete listener for testing registerListener."""

class TestTask(TestCase):

    # -------------------------------------------------------------------------#
    # __init__                                                                 #
    # -------------------------------------------------------------------------#

    def testInitStoresSignature(self):
        """
        Test that __init__ stores the given signature.

        Calling entity() after configuring a trigger should produce a TaskEntity
        whose signature matches the one passed at construction time.
        """
        task = _make_task(signature="my:cmd")
        task.everySeconds(1)
        entity = task.entity()
        self.assertEqual(entity.signature, "my:cmd")

    def testInitWithNoneArgsDefaultsToEmptyList(self):
        """
        Test that passing None as args initialises the internal list to empty.

        Ensures that the TaskEntity receives an empty list rather than None
        when no arguments are provided.
        """
        task = _make_task(args=None)
        task.everySeconds(1)
        entity = task.entity()
        self.assertEqual(entity.args, [])

    def testInitWithExplicitArgsList(self):
        """
        Test that an explicit args list is preserved through to the entity.

        Verifies that arguments passed to the constructor are stored and later
        accessible via entity().
        """
        task = _make_task(args=["--verbose", "--output=json"])
        task.everySeconds(1)
        entity = task.entity()
        self.assertEqual(entity.args, ["--verbose", "--output=json"])

    def testInitWithPurpose(self):
        """
        Test that a purpose string passed at construction is stored correctly.

        Verifies the initial purpose value appears in the resulting TaskEntity.
        """
        task = _make_task(purpose="My task purpose")
        task.everySeconds(1)
        entity = task.entity()
        self.assertEqual(entity.purpose, "My task purpose")

    def testInitDefaultCoalesceIsTrue(self):
        """
        Test that coalesce defaults to True on initialisation.

        Ensures the default coalesce value is propagated to the TaskEntity.
        """
        task = _make_task()
        task.everySeconds(1)
        entity = task.entity()
        self.assertTrue(entity.coalesce)

    def testInitDefaultMaxInstancesIsOne(self):
        """
        Test that max_instances defaults to 1 on initialisation.

        Verifies the default concurrency limit is preserved in the TaskEntity.
        """
        task = _make_task()
        task.everySeconds(1)
        entity = task.entity()
        self.assertEqual(entity.max_instances, 1)

    # -------------------------------------------------------------------------#
    # entity                                                                   #
    # -------------------------------------------------------------------------#

    def testEntityRaisesValueErrorWithoutTrigger(self):
        """
        Test that entity() raises ValueError when no trigger has been set.

        Ensures that a task without a scheduling trigger cannot produce a
        valid TaskEntity.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.entity()

    def testEntityRaisesValueErrorWithEmptySignature(self):
        """
        Test that entity() raises ValueError when the signature is an empty string.

        An empty signature is falsy and should prevent the entity from being built.
        """
        task = _make_task(signature="")
        task.everySeconds(5)
        with self.assertRaises(ValueError):
            task.entity()

    def testEntityReturnsTaskEntityInstance(self):
        """
        Test that entity() returns a TaskEntity after a trigger has been configured.

        Verifies the return type when both signature and trigger are present.
        """
        task = _make_task(signature="run:cmd")
        task.everySeconds(10)
        entity = task.entity()
        self.assertIsInstance(entity, TaskEntity)

    # -------------------------------------------------------------------------#
    # coalesce                                                                 #
    # -------------------------------------------------------------------------#

    def testCoalesceDefaultIsTrueInEntity(self):
        """
        Test that coalesce is True by default in the produced TaskEntity.

        Ensures baseline behaviour without calling coalesce() explicitly.
        """
        task = _make_task()
        task.everySeconds(1)
        self.assertTrue(task.entity().coalesce)

    def testCoalesceSetFalse(self):
        """
        Test that coalesce(False) correctly sets the coalesce flag to False.

        Verifies that the TaskEntity reflects the updated coalesce configuration.
        """
        task = _make_task()
        task.everySeconds(1)
        task.coalesce(coalesce=False)
        self.assertFalse(task.entity().coalesce)

    def testCoalesceReturnsSelf(self):
        """
        Test that coalesce() returns the Task instance for method chaining.

        Ensures the fluent interface is maintained.
        """
        task = _make_task()
        result = task.coalesce(coalesce=True)
        self.assertIs(result, task)

    # -------------------------------------------------------------------------#
    # misfireGraceTime                                                         #
    # -------------------------------------------------------------------------#

    def testMisfireGraceTimeValidSeconds(self):
        """
        Test that misfireGraceTime() accepts a valid positive integer.

        Verifies that the grace period is stored and reflected in the entity.
        """
        task = _make_task()
        task.misfireGraceTime(120)
        task.everySeconds(1)
        entity = task.entity()
        self.assertEqual(entity.misfire_grace_time, 120)

    def testMisfireGraceTimeInvalidZeroRaisesError(self):
        """
        Test that misfireGraceTime(0) raises a ValueError.

        Zero is not a positive integer and must be rejected.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.misfireGraceTime(0)

    def testMisfireGraceTimeNegativeRaisesError(self):
        """
        Test that a negative value for misfireGraceTime raises a ValueError.

        Negative integers are invalid for a grace period.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.misfireGraceTime(-5)

    def testMisfireGraceTimeNonIntegerRaisesError(self):
        """
        Test that a non-integer value for misfireGraceTime raises a ValueError.

        Only integer types are accepted for the misfire grace period.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.misfireGraceTime(30.5)

    def testMisfireGraceTimeReturnsSelf(self):
        """
        Test that misfireGraceTime() returns the Task instance for chaining.

        Ensures the fluent builder interface is correctly maintained.
        """
        task = _make_task()
        result = task.misfireGraceTime(60)
        self.assertIs(result, task)

    # -------------------------------------------------------------------------#
    # purpose                                                                  #
    # -------------------------------------------------------------------------#

    def testPurposeValidString(self):
        """
        Test that purpose() accepts a valid non-empty string.

        Verifies the purpose is stored and reflected in the TaskEntity.
        """
        task = _make_task()
        task.purpose("Runs nightly cleanup")
        task.everySeconds(1)
        entity = task.entity()
        self.assertEqual(entity.purpose, "Runs nightly cleanup")

    def testPurposeStripsWhitespace(self):
        """
        Test that purpose() strips surrounding whitespace from the value.

        Ensures the stored purpose is a clean string.
        """
        task = _make_task()
        task.purpose("  Runs cleanup  ")
        task.everySeconds(1)
        entity = task.entity()
        self.assertEqual(entity.purpose, "Runs cleanup")

    def testPurposeEmptyStringRaisesError(self):
        """
        Test that purpose() raises ValueError for an empty string.

        An empty or blank purpose is not meaningful and must be rejected.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.purpose("")

    def testPurposeWhitespaceOnlyRaisesError(self):
        """
        Test that purpose() raises ValueError for a whitespace-only string.

        A string consisting only of spaces does not constitute a valid purpose.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.purpose("   ")

    def testPurposeNonStringRaisesError(self):
        """
        Test that purpose() raises ValueError for a non-string argument.

        Only strings are valid for the purpose field.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.purpose(123)

    def testPurposeReturnsSelf(self):
        """
        Test that purpose() returns the Task instance for method chaining.

        Ensures the fluent builder interface is correctly maintained.
        """
        task = _make_task()
        result = task.purpose("Testing")
        self.assertIs(result, task)

    # -------------------------------------------------------------------------#
    # startDate   / endDate                                                    #
    # -------------------------------------------------------------------------#

    def testStartDateValidComponentsStoresDatetime(self):
        """
        Test that startDate() accepts valid integer components and stores a datetime.

        Verifies the resulting entity's start_date matches all given components.
        """
        task = _make_task()
        task.startDate(2030, 6, 15, 8, 30, 0)
        task.everySeconds(1)
        entity = task.entity()
        self.assertIsInstance(entity.start_date, datetime)
        self.assertEqual(entity.start_date.year, 2030)
        self.assertEqual(entity.start_date.month, 6)
        self.assertEqual(entity.start_date.day, 15)
        self.assertEqual(entity.start_date.hour, 8)
        self.assertEqual(entity.start_date.minute, 30)
        self.assertEqual(entity.start_date.second, 0)

    def testStartDateDefaultsOptionalComponentsToZero(self):
        """
        Test that startDate() defaults hour, minute, and second to zero.

        When only year, month, and day are supplied, the time components
        should each default to zero.
        """
        task = _make_task()
        task.startDate(2030, 1, 1)
        task.everySeconds(1)
        entity = task.entity()
        self.assertEqual(entity.start_date.hour, 0)
        self.assertEqual(entity.start_date.minute, 0)
        self.assertEqual(entity.start_date.second, 0)

    def testStartDateInvalidYearTypeRaisesTypeError(self):
        """
        Test that startDate() raises TypeError when year is not an integer.

        Non-integer year values must be rejected.
        """
        task = _make_task()
        with self.assertRaises(TypeError):
            task.startDate("2030", 1, 1)

    def testStartDateInvalidHourRaisesValueError(self):
        """
        Test that startDate() raises ValueError for hour outside [0, 23].

        An hour of 24 is not valid.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.startDate(2030, 1, 1, hour=24)

    def testStartDateInvalidMinuteRaisesValueError(self):
        """
        Test that startDate() raises ValueError for minute outside [0, 59].

        A minute of 60 is not valid.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.startDate(2030, 1, 1, minute=60)

    def testStartDateInvalidSecondRaisesValueError(self):
        """
        Test that startDate() raises ValueError for second outside [0, 59].

        A second of 60 is not valid.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.startDate(2030, 1, 1, second=60)

    def testStartDateReturnsSelf(self):
        """
        Test that startDate() returns the Task instance for chaining.

        Ensures the fluent builder interface is correctly maintained.
        """
        task = _make_task()
        result = task.startDate(2030, 1, 1)
        self.assertIs(result, task)

    def testEndDateValidComponentsStoresDatetime(self):
        """
        Test that endDate() accepts valid integer components and stores a datetime.

        Verifies the resulting entity's end_date matches all given components.
        """
        task = _make_task()
        task.endDate(2030, 12, 31, 23, 59, 59)
        task.everySeconds(1)
        entity = task.entity()
        self.assertIsInstance(entity.end_date, datetime)
        self.assertEqual(entity.end_date.year, 2030)
        self.assertEqual(entity.end_date.month, 12)
        self.assertEqual(entity.end_date.day, 31)
        self.assertEqual(entity.end_date.hour, 23)
        self.assertEqual(entity.end_date.minute, 59)
        self.assertEqual(entity.end_date.second, 59)

    def testEndDateDefaultsOptionalComponentsToZero(self):
        """
        Test that endDate() defaults hour, minute, and second to zero.

        When only year, month, and day are supplied, the time components
        should each default to zero.
        """
        task = _make_task()
        task.endDate(2030, 12, 31)
        task.everySeconds(1)
        entity = task.entity()
        self.assertEqual(entity.end_date.hour, 0)
        self.assertEqual(entity.end_date.minute, 0)
        self.assertEqual(entity.end_date.second, 0)

    def testEndDateInvalidMonthTypeRaisesTypeError(self):
        """
        Test that endDate() raises TypeError when month is not an integer.

        Non-integer month values must be rejected.
        """
        task = _make_task()
        with self.assertRaises(TypeError):
            task.endDate(2030, "12", 31)

    def testEndDateInvalidHourRaisesValueError(self):
        """
        Test that endDate() raises ValueError for hour outside [0, 23].

        An hour of 24 is not valid.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.endDate(2030, 12, 31, hour=24)

    def testEndDateInvalidMinuteRaisesValueError(self):
        """
        Test that endDate() raises ValueError for minute outside [0, 59].

        A minute of 60 is not valid.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.endDate(2030, 12, 31, minute=60)

    def testEndDateInvalidSecondRaisesValueError(self):
        """
        Test that endDate() raises ValueError for second outside [0, 59].

        A second of 60 is not valid.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.endDate(2030, 12, 31, second=60)

    def testEndDateReturnsSelf(self):
        """
        Test that endDate() returns the Task instance for chaining.

        Ensures the fluent builder interface is correctly maintained.
        """
        task = _make_task()
        result = task.endDate(2030, 12, 31)
        self.assertIs(result, task)

    # -------------------------------------------------------------------------#
    # randomDelay                                                              #
    # -------------------------------------------------------------------------#

    def testRandomDelayZeroDisablesJitter(self):
        """
        Test that randomDelay(0) sets the internal delay to zero.

        Verifies that zero is accepted and the entity reflects no jitter.
        """
        task = _make_task()
        task.randomDelay(0)
        task.everyMinutes(1)
        entity = task.entity()
        self.assertEqual(entity.random_delay, 0)

    def testRandomDelayValidPositiveInt(self):
        """
        Test that randomDelay() accepts a value between 1 and 120.

        Ensures a random delay in range is stored (as a value ≥ 1).
        """
        task = _make_task()
        result = task.randomDelay(60)
        self.assertIs(result, task)

    def testRandomDelayNegativeRaisesError(self):
        """
        Test that randomDelay() raises ValueError for a negative value.

        Negative values are outside the valid [0, 120] range.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.randomDelay(-1)

    def testRandomDelayAbove120RaisesError(self):
        """
        Test that randomDelay() raises ValueError for values above 120.

        Values greater than 120 are outside the permitted range.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.randomDelay(121)

    def testRandomDelayNonIntegerRaisesError(self):
        """
        Test that randomDelay() raises ValueError for non-integer types.

        Floats and other non-integer types must be rejected.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.randomDelay(10.5)

    def testRandomDelayReturnsSelf(self):
        """
        Test that randomDelay() returns the Task instance for chaining.

        Ensures the fluent builder interface is correctly maintained.
        """
        task = _make_task()
        result = task.randomDelay(10)
        self.assertIs(result, task)

    # -------------------------------------------------------------------------#
    # maxInstances                                                             #
    # -------------------------------------------------------------------------#

    def testMaxInstancesValidPositiveInt(self):
        """
        Test that maxInstances() accepts a positive integer.

        Verifies the value is stored and accessible through the TaskEntity.
        """
        task = _make_task()
        task.maxInstances(3)
        task.everySeconds(1)
        entity = task.entity()
        self.assertEqual(entity.max_instances, 3)

    def testMaxInstancesZeroRaisesError(self):
        """
        Test that maxInstances(0) raises a ValueError.

        Zero concurrent instances is invalid.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.maxInstances(0)

    def testMaxInstancesNegativeRaisesError(self):
        """
        Test that a negative maxInstances value raises a ValueError.

        Negative instance counts are not meaningful.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.maxInstances(-2)

    def testMaxInstancesReturnsSelf(self):
        """
        Test that maxInstances() returns the Task instance for chaining.

        Ensures the fluent builder interface is correctly maintained.
        """
        task = _make_task()
        result = task.maxInstances(5)
        self.assertIs(result, task)

    # -------------------------------------------------------------------------#
    # on                                                                       #
    # -------------------------------------------------------------------------#

    def testOnRegistersCallbackForEvent(self):
        """
        Test that on() registers a callback for a given TaskEvent.

        Verifies that after calling on(), the listener is present in the entity.
        """
        task = _make_task()
        callback = MagicMock()
        task.on(TaskEvent.ADDED, callback)
        task.everySeconds(1)
        entity = task.entity()
        registered_callbacks = [cb for _, cb in entity.listeners]
        self.assertIn(callback, registered_callbacks)

    def testOnInvalidEventRaisesTypeError(self):
        """
        Test that on() raises TypeError when the event is not a TaskEvent.

        Passing a string or integer instead of a TaskEvent must be rejected.
        """
        task = _make_task()
        with self.assertRaises(TypeError):
            task.on("added", lambda: None)

    def testOnNonCallableCallbackRaisesTypeError(self):
        """
        Test that on() raises TypeError when the callback is not callable.

        A non-callable value such as a string must be rejected.
        """
        task = _make_task()
        with self.assertRaises(TypeError):
            task.on(TaskEvent.EXECUTED, "not_a_callable")

    def testOnReturnsSelf(self):
        """
        Test that on() returns the Task instance for method chaining.

        Ensures the fluent builder interface is correctly maintained.
        """
        task = _make_task()
        result = task.on(TaskEvent.ERROR, lambda: None)
        self.assertIs(result, task)

    def testOnMultipleEventsRegistered(self):
        """
        Test that multiple calls to on() accumulate all registered listeners.

        Verifies that each registered (event, callback) pair is preserved.
        """
        task = _make_task()
        cb1, cb2 = MagicMock(), MagicMock()
        task.on(TaskEvent.ADDED, cb1)
        task.on(TaskEvent.EXECUTED, cb2)
        task.everySeconds(1)
        entity = task.entity()
        self.assertEqual(len(entity.listeners), 2)

    # -------------------------------------------------------------------------#
    # registerListener                                                         #
    # -------------------------------------------------------------------------#

    def testRegisterListenerWithInstanceReturnsSelf(self):
        """
        Test that registerListener() accepts a BaseTaskListener subclass instance.

        Verifies the method does not raise and returns self for chaining.
        """
        task = _make_task()
        listener = _ConcreteListener()
        result = task.registerListener(listener)
        self.assertIs(result, task)

    def testRegisterListenerInvalidTypeRaisesTypeError(self):
        """
        Test that registerListener() raises TypeError for non-BaseTaskListener types.

        Passing an arbitrary object must be rejected with a TypeError.
        """
        task = _make_task()
        with self.assertRaises(TypeError):
            task.registerListener(object())

    def testRegisterListenerClassDirectlyRaisesTypeError(self):
        """
        Test that registerListener() raises TypeError when passed a class directly.

        The reverted implementation only accepts instances of BaseTaskListener;
        passing the class itself must be rejected.
        """
        task = _make_task()
        with self.assertRaises(TypeError):
            task.registerListener(_ConcreteListener)

    def testRegisterListenerRegistersCallableMethods(self):
        """
        Test that registerListener() registers callable listener methods as handlers.

        Verifies that a listener method (e.g., onTaskAdded) is mapped to its
        corresponding TaskEvent and added to the internal listeners collection.
        """
        class _CountingListener(BaseTaskListener):
            def onTaskAdded(self, event):
                pass

        task = _make_task()
        listener = _CountingListener()
        task.registerListener(listener)
        task.everySeconds(1)
        entity = task.entity()
        registered_events = [ev for ev, _ in entity.listeners]
        self.assertIn(TaskEvent.ADDED, registered_events)

    def testRegisterListenerRegistersAllMappedEvents(self):
        """
        Test that registerListener() registers all overridden listener methods.

        A listener that overrides multiple handler methods should have each
        method mapped to its corresponding TaskEvent in the entity's listeners.
        """
        class _FullListener(BaseTaskListener):
            def onTaskAdded(self, event): pass
            def onTaskExecuted(self, event): pass
            def onTaskError(self, event): pass

        task = _make_task()
        task.registerListener(_FullListener())
        task.everySeconds(1)
        entity = task.entity()
        registered_events = [ev for ev, _ in entity.listeners]
        self.assertIn(TaskEvent.ADDED, registered_events)
        self.assertIn(TaskEvent.EXECUTED, registered_events)
        self.assertIn(TaskEvent.ERROR, registered_events)

    def testRegisterListenerNonBaseListenerInstanceRaisesTypeError(self):
        """
        Test that registerListener() raises TypeError for non-BaseTaskListener objects.

        Even a duck-typed object with the right methods must be rejected
        if it does not inherit from BaseTaskListener.
        """
        class _FakeListener:
            def onTaskAdded(self, event): pass

        task = _make_task()
        with self.assertRaises(TypeError):
            task.registerListener(_FakeListener())

    # -------------------------------------------------------------------------#
    # onceAt                                                                   #
    # -------------------------------------------------------------------------#

    def testOnceAtValidComponentsReturnsTrue(self):
        """
        Test that onceAt() with valid integer components returns True.

        Verifies the basic success path for one-time task scheduling.
        """
        task = _make_task()
        result = task.onceAt(2030, 6, 15, 10, 30, 0)
        self.assertTrue(result)

    def testOnceAtSetsDateTrigger(self):
        """
        Test that onceAt() configures a DateTrigger in the resulting entity.

        Verifies the correct trigger type is used for one-time execution.
        """
        task = _make_task()
        task.onceAt(2030, 6, 15, 10, 0, 0)
        entity = task.entity()
        self.assertIsInstance(entity.trigger, DateTrigger)

    def testOnceAtSetsMaxInstancesToOne(self):
        """
        Test that onceAt() forces max_instances to 1 regardless of prior configuration.

        Ensures a one-time task can only have a single concurrent instance.
        """
        task = _make_task()
        task.maxInstances(5)
        task.onceAt(2030, 6, 15, 10, 0, 0)
        entity = task.entity()
        self.assertEqual(entity.max_instances, 1)

    def testOnceAtSetsStartAndEndDateToSameValue(self):
        """
        Test that onceAt() sets start_date and end_date to the same datetime.

        A one-time execution has identical start and end boundaries.
        """
        task = _make_task()
        task.onceAt(2030, 6, 15, 10, 0, 0)
        entity = task.entity()
        self.assertEqual(entity.start_date, entity.end_date)

    def testOnceAtDefaultsOptionalComponentsToZero(self):
        """
        Test that onceAt() defaults hour, minute, and second to zero.

        When only year, month, and day are given, the time defaults to midnight.
        """
        task = _make_task()
        task.onceAt(2030, 1, 1)
        entity = task.entity()
        self.assertEqual(entity.start_date.hour, 0)
        self.assertEqual(entity.start_date.minute, 0)
        self.assertEqual(entity.start_date.second, 0)

    def testOnceAtInvalidYearTypeRaisesTypeError(self):
        """
        Test that onceAt() raises TypeError when year is not an integer.

        Non-integer date components must be rejected.
        """
        task = _make_task()
        with self.assertRaises(TypeError):
            task.onceAt("2030", 1, 1)

    def testOnceAtInvalidHourRaisesValueError(self):
        """
        Test that onceAt() raises ValueError for hour outside [0, 23].

        An hour of 24 is not valid.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.onceAt(2030, 1, 1, hour=24)

    def testOnceAtWithRandomDelayRaisesValueError(self):
        """
        Test that onceAt() raises ValueError when a random delay has been set.

        A one-time execution cannot use jitter since it has a fixed run date.
        """
        task = _make_task()
        # Force a non-zero random delay directly to avoid flakiness
        # (randomDelay(n) uses secrets.randbelow which can return 0)
        task._Task__random_delay = 5  # type: ignore[attr-defined]
        with self.assertRaises(ValueError):
            task.onceAt(2030, 6, 15, 10, 0, 0)

    # -------------------------------------------------------------------------#
    # everySeconds                                                             #
    # -------------------------------------------------------------------------#

    def testEverySecondsValidReturnsTrue(self):
        """
        Test that everySeconds() with a positive integer returns True.

        Verifies the success path for seconds-based interval scheduling.
        """
        task = _make_task()
        result = task.everySeconds(30)
        self.assertTrue(result)

    def testEverySecondsSetsIntervalTrigger(self):
        """
        Test that everySeconds() configures an IntervalTrigger.

        Ensures the correct trigger type is used for seconds-based intervals.
        """
        task = _make_task()
        task.everySeconds(10)
        entity = task.entity()
        self.assertIsInstance(entity.trigger, IntervalTrigger)

    def testEverySecondsOneSetsDetailsCorrectly(self):
        """
        Test that everySeconds(1) sets the details to 'Every second'.

        Verifies the singular form is used when interval is exactly one second.
        """
        task = _make_task()
        task.everySeconds(1)
        entity = task.entity()
        self.assertEqual(entity.details, "Every second")

    def testEverySecondsMultipleSetsDetailsCorrectly(self):
        """
        Test that everySeconds(N) sets the details to 'Every N seconds'.

        Verifies the plural form is used when the interval is more than one second.
        """
        task = _make_task()
        task.everySeconds(15)
        entity = task.entity()
        self.assertEqual(entity.details, "Every 15 seconds")

    def testEverySecondsZeroRaisesValueError(self):
        """
        Test that everySeconds(0) raises a ValueError.

        Zero is not a positive integer and must be rejected.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.everySeconds(0)

    def testEverySecondsNegativeRaisesValueError(self):
        """
        Test that a negative value for everySeconds raises a ValueError.

        Negative intervals are not valid.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.everySeconds(-5)

    def testEverySecondsWithRandomDelayRaisesValueError(self):
        """
        Test that everySeconds() raises ValueError when random delay is active.

        Second-based intervals do not support jitter and must reject the combination.
        """
        task = _make_task()
        with patch(
            "orionis.console.fluent.task.secrets.randbelow",
            return_value=5,
        ):
            task.randomDelay(5)
        with self.assertRaises(ValueError):
            task.everySeconds(10)

    # -------------------------------------------------------------------------#
    # Delegation helpers (everyFiveSeconds, everyTenSeconds …)                 #
    # -------------------------------------------------------------------------#

    def testEveryFiveSecondsDelegatesToEverySeconds(self):
        """
        Test that everyFiveSeconds() results in a 5-second IntervalTrigger.

        Verifies the delegation produces the expected trigger and returns True.
        """
        task = _make_task()
        result = task.everyFiveSeconds()
        self.assertTrue(result)
        entity = task.entity()
        self.assertIsInstance(entity.trigger, IntervalTrigger)

    def testEveryFiftyFiveSecondsDelegatesToEverySeconds(self):
        """
        Test that everyFiftyFiveSeconds() results in a 55-second IntervalTrigger.

        Verifies the upper-bound delegation helper works correctly.
        """
        task = _make_task()
        result = task.everyFiftyFiveSeconds()
        self.assertTrue(result)
        entity = task.entity()
        self.assertEqual(entity.details, "Every 55 seconds")

    # -------------------------------------------------------------------------#
    # everyMinutes   / everyMinuteAt   / everyMinutesAt                        #
    # -------------------------------------------------------------------------#

    def testEveryMinutesValidReturnsTrue(self):
        """
        Test that everyMinutes() with a positive integer returns True.

        Verifies the basic success path for minutes-based interval scheduling.
        """
        task = _make_task()
        result = task.everyMinutes(5)
        self.assertTrue(result)

    def testEveryMinutesZeroRaisesValueError(self):
        """
        Test that everyMinutes(0) raises a ValueError.

        Zero is not a positive integer and must be rejected.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.everyMinutes(0)

    def testEveryMinuteAtValidSecondReturnsTrue(self):
        """
        Test that everyMinuteAt() with a valid second (0-59) returns True.

        Verifies the basic success path for per-minute cron-based scheduling.
        """
        task = _make_task()
        result = task.everyMinuteAt(30)
        self.assertTrue(result)

    def testEveryMinuteAtSetsCronTrigger(self):
        """
        Test that everyMinuteAt() configures a CronTrigger.

        Verifies the correct trigger type is selected for this schedule type.
        """
        task = _make_task()
        task.everyMinuteAt(0)
        entity = task.entity()
        self.assertIsInstance(entity.trigger, CronTrigger)

    def testEveryMinuteAtInvalidSecondRaisesValueError(self):
        """
        Test that everyMinuteAt() raises ValueError for second outside [0, 59].

        60 is not a valid second value and must be rejected.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.everyMinuteAt(60)

    def testEveryMinutesAtValidReturnsTrue(self):
        """
        Test that everyMinutesAt() with valid minutes and seconds returns True.

        Verifies the success path for the every-N-minutes at specific-second schedule.
        """
        task = _make_task()
        result = task.everyMinutesAt(10, 30)
        self.assertTrue(result)

    def testEveryMinutesAtInvalidMinutesRaisesValueError(self):
        """
        Test that everyMinutesAt() raises ValueError for non-positive minutes.

        Zero and negatives are invalid interval values.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.everyMinutesAt(0, 0)

    def testEveryMinutesAtInvalidSecondsRaisesValueError(self):
        """
        Test that everyMinutesAt() raises ValueError for seconds outside [0, 59].

        60 is not a valid second value.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.everyMinutesAt(5, 60)

    # -------------------------------------------------------------------------#
    # hourly   / hourlyAt                                                      #
    # -------------------------------------------------------------------------#

    def testHourlyReturnsTrue(self):
        """
        Test that hourly() returns True.

        Verifies the basic success path for hourly scheduling.
        """
        task = _make_task()
        result = task.hourly()
        self.assertTrue(result)

    def testHourlySetsIntervalTrigger(self):
        """
        Test that hourly() configures an IntervalTrigger.

        Verifies the correct trigger type is used for hourly execution.
        """
        task = _make_task()
        task.hourly()
        entity = task.entity()
        self.assertIsInstance(entity.trigger, IntervalTrigger)

    def testHourlyAtValidMinuteSecondReturnsTrue(self):
        """
        Test that hourlyAt() with valid minute and second returns True.

        Verifies the success path for scheduling at a specific time within the hour.
        """
        task = _make_task()
        result = task.hourlyAt(30, 0)
        self.assertTrue(result)

    def testHourlyAtSetsCronTrigger(self):
        """
        Test that hourlyAt() configures a CronTrigger.

        IntervalTrigger does not accept minute/second positioning, so a
        CronTrigger is used to fire at the correct minute:second each hour.
        """
        task = _make_task()
        task.hourlyAt(15, 30)
        entity = task.entity()
        self.assertIsInstance(entity.trigger, CronTrigger)

    def testHourlyAtInvalidMinuteRaisesValueError(self):
        """
        Test that hourlyAt() raises ValueError for minute outside [0, 59].

        60 is not a valid minute value.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.hourlyAt(60)

    def testHourlyAtInvalidSecondRaisesValueError(self):
        """
        Test that hourlyAt() raises ValueError for second outside [0, 59].

        60 is not a valid second value.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.hourlyAt(0, 60)

    def testHourlyAtNonIntegerRaisesTypeError(self):
        """
        Test that hourlyAt() raises TypeError when minute is not an integer.

        Only integer types are accepted for minute and second parameters.
        """
        task = _make_task()
        with self.assertRaises(TypeError):
            task.hourlyAt(30.5)

    # -------------------------------------------------------------------------#
    # everyHours   / everyHoursAt                                              #
    # -------------------------------------------------------------------------#

    def testEveryHoursValidReturnsTrue(self):
        """
        Test that everyHours() with a positive integer returns True.

        Verifies the basic success path for multi-hour interval scheduling.
        """
        task = _make_task()
        result = task.everyHours(6)
        self.assertTrue(result)

    def testEveryHoursZeroRaisesValueError(self):
        """
        Test that everyHours(0) raises a ValueError.

        Zero is not a positive integer and must be rejected.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.everyHours(0)

    def testEveryHoursAtValidReturnsTrue(self):
        """
        Test that everyHoursAt() with valid parameters returns True.

        Verifies the success path for scheduling every N hours at a given time.
        """
        task = _make_task()
        result = task.everyHoursAt(4, 30, 0)
        self.assertTrue(result)

    def testEveryHoursAtSetsCronTrigger(self):
        """
        Test that everyHoursAt() configures a CronTrigger.

        CronTrigger is used instead of IntervalTrigger because the latter
        does not accept minute/second positioning parameters.
        """
        task = _make_task()
        task.everyHoursAt(2, 45, 0)
        entity = task.entity()
        self.assertIsInstance(entity.trigger, CronTrigger)

    def testEveryHoursAtInvalidHourRaisesValueError(self):
        """
        Test that everyHoursAt() raises ValueError for non-positive hours.

        Zero hours is invalid.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.everyHoursAt(0, 0)

    def testEveryHoursAtInvalidMinuteRaisesValueError(self):
        """
        Test that everyHoursAt() raises ValueError for minute outside [0, 59].

        60 is not a valid minute value.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.everyHoursAt(1, 60)

    def testEveryOddHoursSetsCronTrigger(self):
        """
        Test that everyOddHours() configures a CronTrigger for odd hours.

        Verifies the correct trigger type and that the method returns True.
        """
        task = _make_task()
        result = task.everyOddHours()
        self.assertTrue(result)
        entity = task.entity()
        self.assertIsInstance(entity.trigger, CronTrigger)

    def testEveryEvenHoursSetsCronTrigger(self):
        """
        Test that everyEvenHours() configures a CronTrigger for even hours.

        Verifies the correct trigger type and that the method returns True.
        """
        task = _make_task()
        result = task.everyEvenHours()
        self.assertTrue(result)
        entity = task.entity()
        self.assertIsInstance(entity.trigger, CronTrigger)

    # -------------------------------------------------------------------------#
    # daily   / dailyAt                                                        #
    # -------------------------------------------------------------------------#

    def testDailyReturnsTrue(self):
        """
        Test that daily() returns True.

        Verifies the basic success path for daily scheduling.
        """
        task = _make_task()
        result = task.daily()
        self.assertTrue(result)

    def testDailySetsCronTrigger(self):
        """
        Test that daily() configures a CronTrigger.

        Verifies midnight-based daily scheduling uses the correct trigger type.
        """
        task = _make_task()
        task.daily()
        entity = task.entity()
        self.assertIsInstance(entity.trigger, CronTrigger)

    def testDailyAtValidHourReturnsTrue(self):
        """
        Test that dailyAt() with a valid hour returns True.

        Verifies the success path for daily scheduling at a specific time.
        """
        task = _make_task()
        result = task.dailyAt(9, 30, 0)
        self.assertTrue(result)

    def testDailyAtInvalidHourRaisesValueError(self):
        """
        Test that dailyAt() raises ValueError for hour outside [0, 23].

        24 is not a valid hour value.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.dailyAt(24)

    def testDailyAtInvalidMinuteRaisesValueError(self):
        """
        Test that dailyAt() raises ValueError for minute outside [0, 59].

        60 is not a valid minute value.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.dailyAt(10, 60)

    # -------------------------------------------------------------------------#
    # everyDays   / everyDaysAt                                                #
    # -------------------------------------------------------------------------#

    def testEveryDaysValidReturnsTrue(self):
        """
        Test that everyDays() with a positive integer returns True.

        Verifies the success path for multi-day interval scheduling.
        """
        task = _make_task()
        result = task.everyDays(3)
        self.assertTrue(result)

    def testEveryDaysZeroRaisesValueError(self):
        """
        Test that everyDays(0) raises a ValueError.

        Zero is not a positive integer and must be rejected.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.everyDays(0)

    def testEveryDaysAtValidReturnsTrue(self):
        """
        Test that everyDaysAt() with valid parameters returns True.

        Verifies the success path for scheduling every N days at a specific time.
        """
        task = _make_task()
        result = task.everyDaysAt(2, 8, 0, 0)
        self.assertTrue(result)

    # -------------------------------------------------------------------------#
    # Day-of-week scheduling                                                   #
    # -------------------------------------------------------------------------#

    def testEveryMondayAtValidReturnsTrue(self):
        """
        Test that everyMondayAt() with a valid hour returns True.

        Verifies the success path for Monday-specific cron scheduling.
        """
        task = _make_task()
        result = task.everyMondayAt(9)
        self.assertTrue(result)

    def testEveryMondayAtInvalidHourRaisesValueError(self):
        """
        Test that everyMondayAt() raises ValueError for hour outside [0, 23].

        24 is invalid and must be rejected.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.everyMondayAt(24)

    def testEverySundayAtSetsCronTrigger(self):
        """
        Test that everySundayAt() configures a CronTrigger.

        Verifies that day-specific scheduling uses the correct trigger type.
        """
        task = _make_task()
        task.everySundayAt(12)
        entity = task.entity()
        self.assertIsInstance(entity.trigger, CronTrigger)

    # -------------------------------------------------------------------------#
    # weekly   / everyWeeks                                                    #
    # -------------------------------------------------------------------------#

    def testWeeklyReturnsTrue(self):
        """
        Test that weekly() returns True.

        Verifies the basic success path for weekly scheduling.
        """
        task = _make_task()
        result = task.weekly()
        self.assertTrue(result)

    def testWeeklySetsCronTrigger(self):
        """
        Test that weekly() configures a CronTrigger.

        Verifies weekly scheduling (every Sunday) uses the correct trigger type.
        """
        task = _make_task()
        task.weekly()
        entity = task.entity()
        self.assertIsInstance(entity.trigger, CronTrigger)

    def testEveryWeeksValidReturnsTrue(self):
        """
        Test that everyWeeks() with a positive integer returns True.

        Verifies the success path for multi-week interval scheduling.
        """
        task = _make_task()
        result = task.everyWeeks(2)
        self.assertTrue(result)

    def testEveryWeeksZeroRaisesValueError(self):
        """
        Test that everyWeeks(0) raises a ValueError.

        Zero is not a positive integer and must be rejected.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.everyWeeks(0)

    # -------------------------------------------------------------------------#
    # every                                                                    #
    # -------------------------------------------------------------------------#

    def testEveryAllZeroRaisesValueError(self):
        """
        Test that every() raises ValueError when all interval parameters are zero.

        At least one parameter must be greater than zero.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.every(weeks=0, days=0, hours=0, minutes=0, seconds=0)

    def testEveryWithSecondsOnlyReturnsTrue(self):
        """
        Test that every() returns True when only seconds are specified.

        Verifies the success path for a simple every-N-seconds custom interval.
        """
        task = _make_task()
        result = task.every(seconds=45)
        self.assertTrue(result)

    def testEveryWithMultipleIntervalsReturnsTrue(self):
        """
        Test that every() returns True with multiple non-zero interval parameters.

        Verifies the composite interval schedule is configured correctly.
        """
        task = _make_task()
        result = task.every(days=1, hours=2, minutes=30)
        self.assertTrue(result)

    def testEveryWithNegativeValueRaisesValueError(self):
        """
        Test that every() raises ValueError when any parameter is negative.

        Negative interval values are not valid.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.every(seconds=-10)

    def testEverySetsIntervalTrigger(self):
        """
        Test that every() configures an IntervalTrigger.

        Verifies the correct trigger type is used for custom intervals.
        """
        task = _make_task()
        task.every(minutes=15)
        entity = task.entity()
        self.assertIsInstance(entity.trigger, IntervalTrigger)

    # -------------------------------------------------------------------------#
    # cron                                                                     #
    # -------------------------------------------------------------------------#

    def testCronWithHourFieldReturnsTrue(self):
        """
        Test that cron() with a valid hour field returns True.

        Verifies the success path for cron-based scheduling with a single field.
        """
        task = _make_task()
        result = task.cron(hour="9")
        self.assertTrue(result)

    def testCronSetsCronTrigger(self):
        """
        Test that cron() configures a CronTrigger.

        Verifies the correct trigger type is used for cron-expression scheduling.
        """
        task = _make_task()
        task.cron(hour="0", minute="30")
        entity = task.entity()
        self.assertIsInstance(entity.trigger, CronTrigger)

    def testCronAllNoneRaisesValueError(self):
        """
        Test that cron() raises ValueError when all fields are None.

        At least one cron field must be provided.
        """
        task = _make_task()
        with self.assertRaises(ValueError):
            task.cron()

    def testCronWithDayOfWeekFieldReturnsTrue(self):
        """
        Test that cron() with only day_of_week specified returns True.

        Verifies that a single field is sufficient for a valid cron schedule.
        """
        task = _make_task()
        result = task.cron(day_of_week="mon-fri")
        self.assertTrue(result)

    # -------------------------------------------------------------------------#
    # Method chaining end-to-end                                               #
    # -------------------------------------------------------------------------#

    def testFluentChainConfiguresEntityCorrectly(self):
        """
        Test a full fluent chain produces a correctly configured TaskEntity.

        Verifies that multiple builder methods can be chained and all
        configured values appear in the resulting TaskEntity.
        """
        task = (
            _make_task(signature="chain:test")
            .purpose("Chained task")
            .coalesce(coalesce=False)
            .misfireGraceTime(30)
            .maxInstances(2)
            .startDate(2030, 6, 1, 8, 0, 0)
            .endDate(2030, 12, 31, 23, 59, 59)
        )
        task.daily()
        entity = task.entity()

        self.assertEqual(entity.signature, "chain:test")
        self.assertEqual(entity.purpose, "Chained task")
        self.assertFalse(entity.coalesce)
        self.assertEqual(entity.misfire_grace_time, 30)
        self.assertEqual(entity.max_instances, 2)
        self.assertIsNotNone(entity.start_date)
        self.assertEqual(entity.start_date.year, 2030)
        self.assertEqual(entity.start_date.month, 6)
        self.assertIsNotNone(entity.end_date)
        self.assertEqual(entity.end_date.year, 2030)
        self.assertEqual(entity.end_date.month, 12)
        self.assertIsInstance(entity.trigger, CronTrigger)
