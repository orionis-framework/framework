from __future__ import annotations
from dataclasses import fields, is_dataclass
from orionis.console.entities.command import Command
from orionis.support.entities.base import BaseEntity
from orionis.test import TestCase

class _DummyClass:
    """Minimal class used as the obj field in Command fixtures."""


class TestCommandEntity(TestCase):

    def _make(self, **kwargs) -> Command:# noqa: ANN003
        """
        Build a minimal valid Command instance.

        Parameters
        ----------
        **kwargs
            Field overrides applied on top of default values.

        Returns
        -------
        Command
            A Command instance ready for assertions.
        """
        defaults = {
            "obj": _DummyClass,
            "signature": "test:cmd",
            "description": "A test command",
        }
        defaults.update(kwargs)
        return Command(**defaults)

    # ------------------------------------------------------------------ #
    #  Inheritance & type                                                #
    # ------------------------------------------------------------------ #

    def testInheritsFromBaseEntity(self) -> None:
        """
        Verify that Command inherits from BaseEntity.

        Ensures the entity follows the expected class hierarchy and
        can use shared base functionality such as toDict.
        """
        self.assertTrue(issubclass(Command, BaseEntity))

    def testIsDataclass(self) -> None:
        """
        Verify that Command is a dataclass.

        Ensures the class is properly decorated with @dataclass so that
        field introspection and equality checks work correctly.
        """
        self.assertTrue(is_dataclass(Command))

    # ------------------------------------------------------------------ #
    #  Construction — normal cases                                       #
    # ------------------------------------------------------------------ #

    def testCanBeInstantiatedWithRequiredFields(self) -> None:
        """
        Verify that Command can be created with only the required fields.

        Ensures instantiation succeeds when obj, signature, and description
        are provided, and optional fields use their defaults.
        """
        cmd = self._make()
        self.assertIsInstance(cmd, Command)

    def testRequiredFieldsAreStored(self) -> None:
        """
        Verify that required field values are stored correctly.

        Ensures obj, signature, and description are accessible and match
        the values passed at construction time.
        """
        cmd = self._make(
            obj=_DummyClass,
            signature="do:something",
            description="Does something",
        )
        self.assertIs(cmd.obj, _DummyClass)
        self.assertEqual(cmd.signature, "do:something")
        self.assertEqual(cmd.description, "Does something")

    def testDefaultMethod(self) -> None:
        """
        Verify the default value of the method field.

        Ensures that when no method is provided, the field defaults to
        the string 'handle' as declared in the dataclass definition.
        """
        cmd = self._make()
        self.assertEqual(cmd.method, "handle")

    def testDefaultTimestamps(self) -> None:
        """
        Verify the default value of the timestamps field.

        Ensures timestamps defaults to True when not explicitly specified.
        """
        cmd = self._make()
        self.assertTrue(cmd.timestamps)

    def testDefaultArgs(self) -> None:
        """
        Verify that args defaults to None when not provided.

        Ensures the optional argument parser field is None unless
        explicitly set.
        """
        cmd = self._make()
        self.assertIsNone(cmd.args)

    # ------------------------------------------------------------------ #
    #  Construction — custom values                                      #
    # ------------------------------------------------------------------ #

    def testCustomMethod(self) -> None:
        """
        Verify that a custom method name is stored correctly.

        Ensures the method field accepts and retains any string value
        passed at construction time.
        """
        cmd = self._make(method="execute")
        self.assertEqual(cmd.method, "execute")

    def testTimestampsCanBeDisabled(self) -> None:
        """
        Verify that timestamps can be set to False.

        Ensures the boolean field accepts False and stores it without
        coercion or modification.
        """
        cmd = self._make(timestamps=False)
        self.assertFalse(cmd.timestamps)

    def testArgsCanBeSetToAList(self) -> None:
        """
        Verify that args accepts a list value.

        Ensures the args field stores a list without modification when
        one is provided at construction.
        """
        fake_args = [object()]
        cmd = self._make(args=fake_args)
        self.assertIs(cmd.args, fake_args)

    # ------------------------------------------------------------------ #
    #  Edge cases                                                        #
    # ------------------------------------------------------------------ #

    def testSignatureCanBeEmptyString(self) -> None:
        """
        Verify that signature accepts an empty string.

        Ensures no validation prevents an empty string from being stored,
        as validation is the responsibility of the loader layer.
        """
        cmd = self._make(signature="")
        self.assertEqual(cmd.signature, "")

    def testDescriptionCanBeEmptyString(self) -> None:
        """
        Verify that description accepts an empty string.

        Ensures no validation prevents an empty description from being
        stored.
        """
        cmd = self._make(description="")
        self.assertEqual(cmd.description, "")

    def testToDictContainsExpectedKeys(self) -> None:
        """
        Verify that toDict returns all declared fields.

        Ensures the serialisation helper exposes every field defined
        on the Command dataclass.
        """
        cmd = self._make()
        d = cmd.toDict()
        for f in fields(Command):
            self.assertIn(f.name, d)

    def testTwoDifferentInstancesWithSameDataAreEqual(self) -> None:
        """
        Verify that two Command instances with identical data compare as equal.

        Ensures the dataclass equality mechanism works correctly so that
        value-based comparison is used instead of identity.
        """
        a = self._make(signature="x:y", description="desc")
        b = self._make(signature="x:y", description="desc")
        self.assertEqual(a, b)

    def testTwoInstancesWithDifferentSignatureAreNotEqual(self) -> None:
        """
        Verify that Commands with different signatures are not equal.

        Ensures the equality check includes the signature field so that
        distinct commands are distinguished correctly.
        """
        a = self._make(signature="a:cmd")
        b = self._make(signature="b:cmd")
        self.assertNotEqual(a, b)
