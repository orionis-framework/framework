from orionis.orm.factories import exceptions as exceptions_module
from orionis.orm.factories.exceptions import FactoryException
from orionis.test import TestCase

class TestFactoryExceptions(TestCase):
    """Verify factory failures retain exception metadata and their hierarchy."""

    def testConcreteFailuresPreserveMessagesArgumentsAndCauses(self) -> None:
        """Keep all factory failures compatible with the module base exception.

        Returns
        -------
        None
            Verify the complete hierarchy and ordinary Python exception chaining.
        """
        names = {
            "FactoryConcurrencyException",
            "FactoryConfigurationException",
            "FactoryDefinitionException",
            "FactoryDependencyException",
            "FactoryPersistenceException",
        }
        exported = {
            name
            for name, value in vars(exceptions_module).items()
            if isinstance(value, type)
            and issubclass(value, FactoryException)
            and value is not FactoryException
        }
        self.assertEqual(exported, names)
        for name in names:
            exception_type = getattr(exceptions_module, name)
            cause = ValueError("invalid attributes")
            try:
                error_msg = "Factory operation failed."
                raise exception_type(error_msg) from cause
            except FactoryException as error:
                self.assertIs(type(error), exception_type)
                self.assertEqual(str(error), error_msg)
                self.assertEqual(error.args, (error_msg,))
                self.assertIs(error.__cause__, cause)
