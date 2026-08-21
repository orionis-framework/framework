from orionis.schemas.contracts.constraint import IRule
from orionis.schemas.entities.failure import ValidationFailure
from orionis.schemas.rule import Rule
from orionis.test import TestCase

# ---------------------------------------------------------------------------
# Concrete Rule subclasses used to exercise the abstract base
# ---------------------------------------------------------------------------

class _AlwaysValidRule(Rule):
    """Concrete Rule that always passes."""

    __code__ = "always_valid"
    __message__ = "Should not appear."

    def enforce(
        self,
        _field: str,
        _value: object,
        _instance: object,
    ) -> bool:
        """
        Accept every value.

        Parameters
        ----------
        _field : str
            Field name associated with the value.
        _value : object
            Value under validation.
        _instance : object
            Owner of the field value.

        Returns
        -------
        bool
            Always ``True``.
        """
        return True

class _AlwaysInvalidRule(Rule):
    """Concrete Rule that always fails."""

    __code__ = "always_invalid"
    __message__ = "Value is always invalid."

    def enforce(
        self,
        _field: str,
        _value: object,
        _instance: object,
    ) -> bool:
        """
        Reject every value.

        Parameters
        ----------
        _field : str
            Field name associated with the value.
        _value : object
            Value under validation.
        _instance : object
            Owner of the field value.

        Returns
        -------
        bool
            Always ``False``.
        """
        return False

class _BareRule(Rule):
    """Concrete Rule declaring neither ``__code__`` nor ``__message__``."""

    def enforce(
        self,
        _field: str,
        _value: object,
        _instance: object,
    ) -> bool:
        """
        Reject every value.

        Parameters
        ----------
        _field : str
            Field name associated with the value.
        _value : object
            Value under validation.
        _instance : object
            Owner of the field value.

        Returns
        -------
        bool
            Always ``False``.
        """
        return False

class _DelegatingRule(Rule):
    """Concrete Rule delegating ``enforce`` back to the abstract base."""

    def enforce(
        self,
        field: str,
        value: object,
        instance: object,
    ) -> bool:
        """
        Delegate to the not-implemented base method.

        Parameters
        ----------
        field : str
            Field name associated with the value.
        value : object
            Value under validation.
        instance : object
            Owner of the field value.

        Returns
        -------
        bool
            Never returns; the base implementation raises.
        """
        return super().enforce(field, value, instance)

class TestRuleContract(TestCase):

    def testRuleImplementsTheRuleInterface(self) -> None:
        """
        Confirm Rule implements the IRule contract.

        Validates that concrete rules satisfy the interface used by the
        rules executor when binding validators.
        """
        self.assertIsInstance(_AlwaysValidRule(), IRule)

    def testRuleDeclaresSlots(self) -> None:
        """
        Confirm Rule stores its state in slots.

        Validates that the base class avoids per-instance dictionaries.
        """
        self.assertEqual(Rule.__slots__, ("_code", "_message"))

class TestRuleEnforce(TestCase):

    def testBaseEnforceRaisesNotImplementedError(self) -> None:
        """
        Raise NotImplementedError when the base enforce is reached.

        Validates that subclasses are required to provide their own
        implementation of the validation predicate.
        """
        rule = _DelegatingRule()
        with self.assertRaises(NotImplementedError):
            rule.enforce("field", "value", object())

class TestRuleValidate(TestCase):

    def testValidateReturnsNoneOnSuccess(self) -> None:
        """
        Return None when the rule accepts the value.

        Validates that a passing rule produces no failure entity.
        """
        rule = _AlwaysValidRule()
        self.assertIsNone(rule.validate("field", "any_value", object()))

    def testValidateReturnsFailureOnRejection(self) -> None:
        """
        Return a ValidationFailure when the rule rejects the value.

        Validates the failure field and rule code reported to the caller.
        """
        result = _AlwaysInvalidRule().validate("age", 0, object())
        self.assertIsInstance(result, ValidationFailure)
        self.assertEqual(result.field, "age")
        self.assertEqual(result.rule, "always_invalid")

    def testValidateUsesClassMessageByDefault(self) -> None:
        """
        Fall back to the class-level message when none is supplied.

        Validates the message resolution performed at construction time.
        """
        result = _AlwaysInvalidRule().validate("field", "value", object())
        self.assertEqual(result.message, "Value is always invalid.")

    def testValidateUsesConstructorMessageWhenProvided(self) -> None:
        """
        Prefer the constructor message over the class-level message.

        Validates that per-instance overrides reach the failure entity.
        """
        rule = _AlwaysInvalidRule(message="Custom error.")
        result = rule.validate("field", "value", object())
        self.assertEqual(result.message, "Custom error.")

    def testMessageDefaultsToNoneWithoutDeclaration(self) -> None:
        """
        Report a None message when the class declares no message.

        Validates that missing class attributes do not break resolution.
        """
        result = _BareRule().validate("field", "value", object())
        self.assertIsNone(result.message)

    def testCodeDefaultsToLowercasedClassName(self) -> None:
        """
        Derive the rule code from the class name when undeclared.

        Validates the fallback applied when ``__code__`` is missing.
        """
        result = _BareRule().validate("field", "value", object())
        self.assertEqual(result.rule, "_barerule")
