import asyncio
from inspect import iscoroutinefunction
from unittest.mock import patch
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

class _NativeAsyncRule(Rule):
    """Require awaiting native enforcement instead of calling the sync fallback."""

    __code__ = "native_async"
    __message__ = "Value was rejected asynchronously."

    async def enforceAsync(
        self,
        _field: str,
        value: object,
        _instance: object,
    ) -> bool:
        """Yield to the caller's loop before evaluating the value."""
        await asyncio.sleep(0)
        return value == "allowed"

class TestRuleContract(TestCase):

    def testValidateIsAlwaysAsync(self) -> None:
        """Require asynchronous validation in the interface and implementation."""
        self.assertTrue(iscoroutinefunction(IRule.validate))
        self.assertTrue(iscoroutinefunction(Rule.validate))

    def testRuleHasNoAlternateEntryPoint(self) -> None:
        """Keep custom rules on the same single validation API as schemas."""
        self.assertFalse(hasattr(Rule, "validateAsync"))

    def testRuleImplementsTheRuleInterface(self) -> None:
        """Confirm Rule implements the IRule contract.

        Validates that concrete rules satisfy the interface used by the
        rules executor when binding validators.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(_AlwaysValidRule(), IRule)

    def testRuleDeclaresSlots(self) -> None:
        """Confirm Rule stores its state in slots.

        Validates that the base class avoids per-instance dictionaries.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Rule.__slots__, ("_code", "_message"))

class TestRuleEnforce(TestCase):

    def testBaseEnforceRaisesNotImplementedError(self) -> None:
        """Raise NotImplementedError when the base enforce is reached.

        Validates that subclasses are required to provide their own
        implementation of the validation predicate.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = _DelegatingRule()
        with self.assertRaises(NotImplementedError):
            rule.enforce("field", "value", object())

class TestRuleValidate(TestCase):

    async def testNativeAsyncEnforcementIsAwaited(self) -> None:
        """Use native enforcement for both accepted and rejected values."""
        rule = _NativeAsyncRule(message="Custom async error.")
        self.assertIsNone(await rule.validate("field", "allowed", object()))
        failure = await rule.validate("field", "rejected", object())
        self.assertIsInstance(failure, ValidationFailure)
        self.assertEqual(failure.field, "field")
        self.assertEqual(failure.rule, "native_async")
        self.assertEqual(failure.message, "Custom async error.")

    async def testSynchronousRulesDoNotUseWorkerThreads(self) -> None:
        """Keep inexpensive synchronous predicates on the caller's thread."""
        with patch("orionis.schemas.rule.asyncio.to_thread") as offload:
            self.assertIsNone(
                await _AlwaysValidRule().validate("field", "value", object()),
            )
        offload.assert_not_called()

    async def testNativeAsyncErrorsPropagate(self) -> None:
        """Do not turn an unexpected native I/O failure into validation success."""
        message = "Native service failed."
        with (
            patch.object(
                _NativeAsyncRule, "enforceAsync", side_effect=RuntimeError(message),
            ),
            self.assertRaisesRegex(RuntimeError, message),
        ):
            await _NativeAsyncRule().validate("field", "value", object())

    async def testValidateReturnsNoneOnSuccess(self) -> None:
        """Return None when the rule accepts the value.

        Validates that a passing rule produces no failure entity.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = _AlwaysValidRule()
        self.assertIsNone(await rule.validate("field", "any_value", object()))

    async def testValidateReturnsFailureOnRejection(self) -> None:
        """Return a ValidationFailure when the rule rejects the value.

        Validates the failure field and rule code reported to the caller.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await _AlwaysInvalidRule().validate("age", 0, object())
        self.assertIsInstance(result, ValidationFailure)
        self.assertEqual(result.field, "age")
        self.assertEqual(result.rule, "always_invalid")

    async def testValidateUsesClassMessageByDefault(self) -> None:
        """Fall back to the class-level message when none is supplied.

        Validates the message resolution performed at construction time.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await _AlwaysInvalidRule().validate("field", "value", object())
        self.assertEqual(result.message, "Value is always invalid.")

    async def testValidateUsesConstructorMessageWhenProvided(self) -> None:
        """Prefer the constructor message over the class-level message.

        Validates that per-instance overrides reach the failure entity.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        rule = _AlwaysInvalidRule(message="Custom error.")
        result = await rule.validate("field", "value", object())
        self.assertEqual(result.message, "Custom error.")

    async def testMessageDefaultsToNoneWithoutDeclaration(self) -> None:
        """Report a None message when the class declares no message.

        Validates that missing class attributes do not break resolution.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await _BareRule().validate("field", "value", object())
        self.assertIsNone(result.message)

    async def testCodeDefaultsToLowercasedClassName(self) -> None:
        """Derive the rule code from the class name when undeclared.

        Validates the fallback applied when ``__code__`` is missing.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        result = await _BareRule().validate("field", "value", object())
        self.assertEqual(result.rule, "_barerule")
