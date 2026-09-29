import inspect
from abc import ABC
from orionis.test import TestCase
from orionis.console.fluent.contracts.task import ITask

class TestITaskContract(TestCase):

    def testITaskInheritsFromABC(self):
        """Test that ITask inherits from ABC.

        Ensures that the ITask class is an abstract base class,
        enforcing the contract for all concrete implementations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(ITask, ABC))

    def testITaskCannotBeInstantiated(self):
        """Test that ITask cannot be directly instantiated.

        Verifies that attempting to create an instance of ITask raises
        a TypeError because it contains abstract methods.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            ITask()

    def testConcreteSubclassWithoutImplementationCannotBeInstantiated(self):
        """Test that a subclass of ITask without implementations cannot be instantiated.

        Ensures that partial implementation of ITask does not satisfy the
        abstract method requirements.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        class IncompleteTask(ITask):
            pass

        with self.assertRaises(TypeError):
            IncompleteTask()

    def testEntityMethodIsAbstract(self):
        """Test that the entity method is declared abstract in ITask.

        Checks that ITask.entity is listed among the abstract methods,
        requiring concrete subclasses to provide an implementation.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("entity", ITask.__abstractmethods__)

    def testCoalesceMethodIsAbstract(self):
        """Test that the coalesce method is declared abstract in ITask.

        Verifies that coalesce must be implemented by any concrete subclass.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("coalesce", ITask.__abstractmethods__)

    def testMisfireGraceTimeMethodIsAbstract(self):
        """Test that the misfireGraceTime method is declared abstract in ITask.

        Ensures the misfire grace time setter is part of the required interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("misfireGraceTime", ITask.__abstractmethods__)

    def testPurposeMethodIsAbstract(self):
        """Test that the purpose method is declared abstract in ITask.

        Verifies that the purpose/description setter is part of the contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("purpose", ITask.__abstractmethods__)

    def testStartDateMethodIsAbstract(self):
        """Test that the startDate method is declared abstract in ITask.

        Checks that any concrete implementation must define startDate.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("startDate", ITask.__abstractmethods__)

    def testEndDateMethodIsAbstract(self):
        """Test that the endDate method is declared abstract in ITask.

        Checks that any concrete implementation must define endDate.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("endDate", ITask.__abstractmethods__)

    def testRandomDelayMethodIsAbstract(self):
        """Test that the randomDelay method is declared abstract in ITask.

        Verifies that random delay configuration is part of the contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("randomDelay", ITask.__abstractmethods__)

    def testMaxInstancesMethodIsAbstract(self):
        """Test that the maxInstances method is declared abstract in ITask.

        Ensures that concurrent instance limiting must be implemented.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("maxInstances", ITask.__abstractmethods__)

    def testOnMethodIsAbstract(self):
        """Test that the on method is declared abstract in ITask.

        Verifies that event listener registration is part of the interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("on", ITask.__abstractmethods__)

    def testRegisterListenerMethodIsAbstract(self):
        """Test that the registerListener method is declared abstract in ITask.

        Ensures that full listener registration is part of the contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("registerListener", ITask.__abstractmethods__)

    def testOnceAtMethodIsAbstract(self):
        """Test that the onceAt method is declared abstract in ITask.

        Verifies that one-time scheduling must be implemented by concrete classes.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("onceAt", ITask.__abstractmethods__)

    def testEverySecondsMethodIsAbstract(self):
        """Test that the everySeconds method is declared abstract in ITask.

        Ensures that seconds-based interval scheduling is part of the contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("everySeconds", ITask.__abstractmethods__)

    def testEveryMinutesMethodIsAbstract(self):
        """Test that the everyMinutes method is declared abstract in ITask.

        Verifies that minutes-based interval scheduling is part of the contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("everyMinutes", ITask.__abstractmethods__)

    def testHourlyMethodIsAbstract(self):
        """Test that the hourly method is declared abstract in ITask.

        Ensures hourly scheduling must be provided by concrete implementations.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("hourly", ITask.__abstractmethods__)

    def testDailyMethodIsAbstract(self):
        """Test that the daily method is declared abstract in ITask.

        Verifies daily scheduling must be implemented by all subclasses.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("daily", ITask.__abstractmethods__)

    def testWeeklyMethodIsAbstract(self):
        """Test that the weekly method is declared abstract in ITask.

        Checks that weekly scheduling is part of the required interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("weekly", ITask.__abstractmethods__)

    def testEveryWeeksMethodIsAbstract(self):
        """Test that the everyWeeks method is declared abstract in ITask.

        Ensures weeks-based interval scheduling is part of the contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("everyWeeks", ITask.__abstractmethods__)

    def testEveryMethodIsAbstract(self):
        """Test that the every method is declared abstract in ITask.

        Verifies the custom multi-unit interval method is required in all subclasses.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("every", ITask.__abstractmethods__)

    def testCronMethodIsAbstract(self):
        """Test that the cron method is declared abstract in ITask.

        Ensures that cron-expression scheduling is part of the required interface.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIn("cron", ITask.__abstractmethods__)

    def testITaskHasManyAbstractMethods(self):
        """Test that ITask defines a large set of abstract scheduling methods.

        Verifies that the contract is comprehensive and covers a broad range
        of scheduling scenarios.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertGreater(len(ITask.__abstractmethods__), 20)

    def testEntityMethodSignature(self):
        """Test that entity() accepts scheduler-level default overrides.

        Verifies the signature matches the documented contract: random_delay,
        max_instances, and misfire_grace_time are positional-or-keyword, and
        coalesce is keyword-only.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ITask.entity)
        params = list(sig.parameters.keys())
        self.assertEqual(
            params,
            ["self", "random_delay", "max_instances", "misfire_grace_time", "coalesce"],
        )
        self.assertEqual(
            sig.parameters["coalesce"].kind,
            inspect.Parameter.KEYWORD_ONLY,
        )

    def testOnMethodSignature(self):
        """Test that the on() method accepts event and callback parameters.

        Verifies the signature aligns with the documented listener registration
        contract.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ITask.on)
        params = list(sig.parameters.keys())
        self.assertIn("event", params)
        self.assertIn("callback", params)

    def testStartDateMethodSignature(self):
        """Test that startDate() accepts year, month, day, hour, minute, second params.

        Verifies the new integer-component signature replaces any datetime-object API.
        The optional time components must default to zero.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ITask.startDate)
        params = sig.parameters
        self.assertIn("year", params)
        self.assertIn("month", params)
        self.assertIn("day", params)
        self.assertIn("hour", params)
        self.assertIn("minute", params)
        self.assertIn("second", params)
        self.assertEqual(params["hour"].default, 0)
        self.assertEqual(params["minute"].default, 0)
        self.assertEqual(params["second"].default, 0)

    def testEndDateMethodSignature(self):
        """Test that endDate() declares year, month, day, hour, minute, and second.

        Verifies the new integer-component signature and that optional time
        components default to zero.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ITask.endDate)
        params = sig.parameters
        self.assertIn("year", params)
        self.assertIn("month", params)
        self.assertIn("day", params)
        self.assertIn("hour", params)
        self.assertIn("minute", params)
        self.assertIn("second", params)
        self.assertEqual(params["hour"].default, 0)
        self.assertEqual(params["minute"].default, 0)
        self.assertEqual(params["second"].default, 0)

    def testOnceAtMethodSignature(self):
        """Test that onceAt() declares year, month, day, hour, minute, and second.

        Verifies the integer-component signature used for one-time scheduling
        and that optional time components default to zero.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ITask.onceAt)
        params = sig.parameters
        self.assertIn("year", params)
        self.assertIn("month", params)
        self.assertIn("day", params)
        self.assertIn("hour", params)
        self.assertIn("minute", params)
        self.assertIn("second", params)
        self.assertEqual(params["hour"].default, 0)
        self.assertEqual(params["minute"].default, 0)
        self.assertEqual(params["second"].default, 0)

    def testRegisterListenerMethodSignature(self):
        """Test that registerListener() declares a listener parameter for instances.

        Verifies the method accepts a single listener argument. The reverted
        implementation only supports BaseTaskListener instances, not class types.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig = inspect.signature(ITask.registerListener)
        params = list(sig.parameters.keys())
        self.assertIn("listener", params)
        self.assertEqual(len([p for p in params if p != "self"]), 1)
