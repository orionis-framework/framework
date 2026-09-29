from __future__ import annotations
from orionis.console.args.argument import Argument
from orionis.console.entities.command import Command as CommandEntity
from orionis.console.fluent.command import Command
from orionis.console.fluent.contracts.command import ICommand
from orionis.test import TestCase

class _Handler:
    """Minimal concrete class used as command handler in tests."""

    def handle(self) -> None: # NOSONAR
        """Return a completed command result.

        Returns
        -------
        None
            Completes the operation described above.
        """

    def execute(self) -> None: # NOSONAR
        """Run the execute helper.

        Returns
        -------
        None
            Completes the operation described above.
        """

class TestFluentCommand(TestCase):

    def _cmd(self, **kwargs: object) -> Command:
        """
        Build a Command with sensible defaults.

        Parameters
        ----------
        **kwargs
            Overrides applied on top of defaults.

        Returns
        -------
        Command
            A configured Command builder instance.
        """
        defaults = {"signature": "test:cmd", "concrete": _Handler}
        defaults.update(kwargs)
        return Command(**defaults)

    # ------------------------------------------------------------------ #
    #  Interface & instantiation                                         #
    # ------------------------------------------------------------------ #

    def testInheritsFromICommand(self) -> None:
        """Verify that Command inherits from ICommand.

        Ensures the implementation satisfies the abstract interface
        contract and follows the expected class hierarchy.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertTrue(issubclass(Command, ICommand))

    def testCanBeInstantiated(self) -> None:
        """Verify that Command can be created with a valid signature and handler.

        Ensures the constructor completes without errors when both
        required arguments are valid.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = self._cmd()
        self.assertIsInstance(cmd, Command)

    def testDefaultMethodIsHandle(self) -> None:
        """Verify that the default method name is 'handle'.

        Ensures that omitting the method argument uses 'handle' as the
        default execution entry point.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = self._cmd()
        _, entity = cmd.get()
        self.assertEqual(entity.method, "handle")

    def testCustomMethodIsAccepted(self) -> None:
        """Verify that a custom method name is accepted and stored.

        Ensures the method argument can be set to any callable method
        present on the concrete class.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = self._cmd(method="execute")
        _, entity = cmd.get()
        self.assertEqual(entity.method, "execute")

    # ------------------------------------------------------------------ #
    #  Constructor validation                                            #
    # ------------------------------------------------------------------ #

    def testNonClassConcreteRaisesTypeError(self) -> None:
        """Verify that passing a non-class as concrete raises TypeError.

        Ensures the constructor rejects anything that is not a class,
        such as a function or plain string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Command(signature="x:cmd", concrete="not_a_class")

    def testNonStringMethodRaisesTypeError(self) -> None:
        """Verify that passing a non-string method name raises TypeError.

        Ensures the constructor validates that the method argument is a
        string before attempting attribute lookup.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            Command(signature="x:cmd", concrete=_Handler, method=123)

    def testNonExistentMethodRaisesAttributeError(self) -> None:
        """Verify that referencing a method not on the class raises AttributeError.

        Ensures the constructor eagerly validates that the named method
        exists and is callable on the concrete class.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(AttributeError):
            Command(signature="x:cmd", concrete=_Handler, method="nonexistent")

    # ------------------------------------------------------------------ #
    # Tests for timestamp()                                              #
    # ------------------------------------------------------------------ #

    def testTimestampDefaultIsTrue(self) -> None:
        """Verify that timestamps are enabled by default.

        Ensures a freshly constructed Command has timestamps set to True
        before any fluent configuration is applied.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, entity = self._cmd().get()
        self.assertTrue(entity.timestamps)

    def testTimestampCanBeDisabled(self) -> None:
        """Verify that timestamps can be disabled via the fluent method.

        Ensures calling timestamp(enabled=False) stores False on the
        resulting CommandEntity.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, entity = self._cmd().timestamp(enabled=False).get()
        self.assertFalse(entity.timestamps)

    def testTimestampCanBeReEnabled(self) -> None:
        """Verify that timestamps can be re-enabled after being disabled.

        Ensures calling timestamp(enabled=True) after a False call
        stores True on the resulting entity.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, entity = self._cmd().timestamp(enabled=False).timestamp(enabled=True).get()
        self.assertTrue(entity.timestamps)

    def testTimestampReturnsSelf(self) -> None:
        """Verify that timestamp() returns the Command instance for chaining.

        Ensures the return value of timestamp() is the same object,
        enabling fluent method chaining.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = self._cmd()
        result = cmd.timestamp(enabled=True)
        self.assertIs(result, cmd)

    def testTimestampWithNonBoolRaisesTypeError(self) -> None:
        """Verify that passing a non-boolean to timestamp raises TypeError.

        Ensures validation catches misuses like timestamp(enabled=1) or
        timestamp(enabled="yes").

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            self._cmd().timestamp(enabled="yes")

    # ------------------------------------------------------------------ #
    # Tests for description()                                            #
    # ------------------------------------------------------------------ #

    def testDescriptionDefaultIsPlaceholder(self) -> None:
        """Verify that a default placeholder description is set.

        Ensures a freshly constructed Command has a non-empty description
        before any fluent configuration.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, entity = self._cmd().get()
        self.assertIsInstance(entity.description, str)
        self.assertGreater(len(entity.description), 0)

    def testDescriptionIsStored(self) -> None:
        """Verify that a custom description is stored on the entity.

        Ensures calling description() updates the CommandEntity's
        description field to the supplied string.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, entity = self._cmd().description("Sends a welcome email").get()
        self.assertEqual(entity.description, "Sends a welcome email")

    def testDescriptionReturnsSelf(self) -> None:
        """Verify that description() returns the Command instance for chaining.

        Ensures the builder pattern is maintained so multiple fluent
        calls can be chained without breaking the chain.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = self._cmd()
        result = cmd.description("desc")
        self.assertIs(result, cmd)

    def testDescriptionWithNonStringRaisesTypeError(self) -> None:
        """Verify that passing a non-string description raises TypeError.

        Ensures the method rejects integers, lists, and other non-string
        types.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            self._cmd().description(123)

    def testDescriptionCanBeEmptyString(self) -> None:
        """Verify that an empty string is accepted as a description.

        Ensures no validation prevents an empty description since the
        caller may intentionally suppress it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, entity = self._cmd().description("").get()
        self.assertEqual(entity.description, "")

    # ------------------------------------------------------------------ #
    #  Tests for arguments()                                             #
    # ------------------------------------------------------------------ #

    def testArgumentsDefaultIsEmptyList(self) -> None:
        """Verify that the default arguments list is empty.

        Ensures a freshly constructed Command has no CLI arguments
        unless explicitly configured.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, entity = self._cmd().get()
        self.assertEqual(entity.args, [])

    def testArgumentsIsStored(self) -> None:
        """Verify that a list of Argument instances is stored correctly.

        Ensures the arguments() method updates the entity's args field
        to the supplied list.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        arg = Argument(name_or_flags="--name", dest="name")
        _, entity = self._cmd().arguments([arg]).get()
        self.assertEqual(entity.args, [arg])

    def testArgumentsReturnsSelf(self) -> None:
        """Verify that arguments() returns the Command instance for chaining.

        Ensures the builder pattern is maintained after setting arguments.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        cmd = self._cmd()
        result = cmd.arguments([])
        self.assertIs(result, cmd)

    def testArgumentsWithNonListRaisesTypeError(self) -> None:
        """Verify that passing a non-list to arguments raises TypeError.

        Ensures the method rejects tuples, sets, and other non-list
        iterables.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            self._cmd().arguments("--name")

    def testArgumentsWithNonArgumentElementRaisesTypeError(self) -> None:
        """Verify that a list containing non-Argument elements raises TypeError.

        Ensures each element in the list is validated to be an instance
        of Argument, rejecting plain strings or dicts.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        with self.assertRaises(TypeError):
            self._cmd().arguments(["--name"])

    def testArgumentsWithMultipleValidArgs(self) -> None:
        """Verify that multiple Argument instances are stored correctly.

        Ensures the arguments list can hold more than one entry without
        modification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        a = Argument(name_or_flags="--foo", dest="foo")
        b = Argument(name_or_flags="--bar", dest="bar")
        _, entity = self._cmd().arguments([a, b]).get()
        self.assertEqual(len(entity.args), 2)

    # ------------------------------------------------------------------ #
    #  Tests for get()                                                   #
    # ------------------------------------------------------------------ #

    def testGetReturnsTuple(self) -> None:
        """Verify that get() returns a tuple.

        Ensures the return type matches the interface contract of
        tuple[str, CommandEntity].

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = self._cmd().get()
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)

    def testGetFirstElementIsSignature(self) -> None:
        """Verify that the first element of the get() tuple is the signature string.

        Ensures the signature passed to the constructor is accessible
        via the tuple returned by get().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        sig, _ = self._cmd(signature="greet:world").get()
        self.assertEqual(sig, "greet:world")

    def testGetSecondElementIsCommandEntity(self) -> None:
        """Verify that the second element of the get() tuple is a CommandEntity.

        Ensures the builder produces a proper CommandEntity instance
        rather than a raw dict or other type.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, entity = self._cmd().get()
        self.assertIsInstance(entity, CommandEntity)

    def testGetEntitySignatureMatchesConstructorSignature(self) -> None:
        """Verify that the CommandEntity's signature matches the builder's signature.

        Ensures the signature propagates correctly from the constructor
        into the entity returned by get().

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, entity = self._cmd(signature="hello:cmd").get()
        self.assertEqual(entity.signature, "hello:cmd")

    def testGetEntityObjIsConcreteClass(self) -> None:
        """Verify that the CommandEntity's obj field is the concrete class.

        Ensures the handler class reference is stored on the entity and
        accessible for dependency injection.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        _, entity = self._cmd().get()
        self.assertIs(entity.obj, _Handler)

    # ------------------------------------------------------------------ #
    #  Full fluent chain                                                 #
    # ------------------------------------------------------------------ #

    def testFullFluentChainProducesCorrectEntity(self) -> None:
        """Verify that chaining all fluent methods produces a correct CommandEntity.

        Ensures the entire builder API works together: timestamp,
        description, and arguments are all reflected in the final entity.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        arg = Argument(name_or_flags="--verbose", dest="verbose")
        sig, entity = (
            Command(signature="send:email", concrete=_Handler)
            .timestamp(enabled=False)
            .description("Send a welcome email")
            .arguments([arg])
            .get()
        )
        self.assertEqual(sig, "send:email")
        self.assertFalse(entity.timestamps)
        self.assertEqual(entity.description, "Send a welcome email")
        self.assertEqual(entity.args, [arg])
        self.assertEqual(entity.method, "handle")
