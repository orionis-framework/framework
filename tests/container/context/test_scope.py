from __future__ import annotations
import contextvars
from orionis.test import TestCase
from orionis.container.context.scope import ScopedContext

class TestScopedContext(TestCase):

    def setUp(self) -> None:
        """Reset scope to None before each test to guarantee isolation.

        Returns
        -------
        None
            Completes the operation described above.
        """
        ScopedContext.setCurrentScope(None)

    def tearDown(self) -> None:
        """Reset scope to None after each test to avoid state leakage.

        Returns
        -------
        None
            Completes the operation described above.
        """
        ScopedContext.setCurrentScope(None)

    # ------------------------------------------------------------------
    # getCurrentScope
    # ------------------------------------------------------------------

    def testGetCurrentScopeDefaultIsNone(self) -> None:
        """
        Test that getCurrentScope returns None when no scope has been set.

        Verifies the default state of the context variable before any
        setCurrentScope call is made.

        Returns
        -------
        None
            This method does not return a value.
        """
        self.assertIsNone(ScopedContext.getCurrentScope())

    def testGetCurrentScopeReturnsSetObject(self) -> None:
        """
        Test that getCurrentScope returns the exact object passed to setCurrentScope.

        Ensures identity (not just equality) is preserved so the caller always
        receives the same object that was stored.

        Returns
        -------
        None
            This method does not return a value.
        """
        scope = object()
        ScopedContext.setCurrentScope(scope)
        self.assertIs(ScopedContext.getCurrentScope(), scope)

    def testGetCurrentScopeAfterSettingNone(self) -> None:
        """
        Test that getCurrentScope returns None after explicitly setting None.

        Confirms that None is a valid scope value and that the context variable
        correctly reflects it as the active scope.

        Returns
        -------
        None
            This method does not return a value.
        """
        ScopedContext.setCurrentScope("initial")
        ScopedContext.setCurrentScope(None)
        self.assertIsNone(ScopedContext.getCurrentScope())

    # ------------------------------------------------------------------
    # setCurrentScope
    # ------------------------------------------------------------------

    def testSetCurrentScopeReturnsContextVarToken(self) -> None:
        """
        Test that setCurrentScope returns a contextvars.Token instance.

        The returned token is required for restoring the previous context
        state via reset(). This verifies the correct return type.

        Returns
        -------
        None
            This method does not return a value.
        """
        token = ScopedContext.setCurrentScope("any_scope")
        self.assertIsInstance(token, contextvars.Token)

    def testSetCurrentScopeOverwritesPreviousScope(self) -> None:
        """
        Test that a second setCurrentScope call replaces the first active scope.

        Verifies that only the most recently set scope is retrievable after
        successive calls.

        Returns
        -------
        None
            This method does not return a value.
        """
        scope_first = {"id": "first"}
        scope_second = {"id": "second"}

        ScopedContext.setCurrentScope(scope_first)
        ScopedContext.setCurrentScope(scope_second)

        self.assertIs(ScopedContext.getCurrentScope(), scope_second)

    def testSetCurrentScopeAcceptsVariousTypes(self) -> None:
        """
        Test that setCurrentScope accepts objects of different Python types.

        Verifies that the context variable places no type restriction on the
        scope value, accepting strings, integers, lists, dicts, and arbitrary
        objects.

        Returns
        -------
        None
            This method does not return a value.
        """
        for obj in ("string_scope", 42, [1, 2, 3], {"key": "val"}, object()):
            ScopedContext.setCurrentScope(obj)
            self.assertIs(ScopedContext.getCurrentScope(), obj)

    # ------------------------------------------------------------------
    # reset
    # ------------------------------------------------------------------

    def testResetRestoresPreviousScopeState(self) -> None:
        """
        Test that reset() restores the scope to the state captured by the token.

        Simulates a nested scope: sets scope A, then scope B, then resets via
        the token obtained before setting B to confirm scope A is restored.

        Returns
        -------
        None
            This method does not return a value.
        """
        scope_a = {"name": "a"}
        scope_b = {"name": "b"}

        ScopedContext.setCurrentScope(scope_a)
        token = ScopedContext.setCurrentScope(scope_b)

        self.assertIs(ScopedContext.getCurrentScope(), scope_b)
        ScopedContext.reset(token)
        self.assertIs(ScopedContext.getCurrentScope(), scope_a)

    def testResetToDefaultNone(self) -> None:
        """
        Test that reset() restores the scope to None when no prior scope existed.

        Captures the token returned by the very first setCurrentScope call
        (starting from the default None state) and verifies that reset()
        brings the scope back to None.

        Returns
        -------
        None
            This method does not return a value.
        """
        token = ScopedContext.setCurrentScope("temporary")
        self.assertEqual(ScopedContext.getCurrentScope(), "temporary")

        ScopedContext.reset(token)
        self.assertIsNone(ScopedContext.getCurrentScope())

    def testResetDoesNotAffectOtherContextVariables(self) -> None:
        """
        Test that reset() only affects the active scope variable and nothing else.

        Confirms that calling reset() on the scope's ContextVar token leaves
        any unrelated context variables untouched.

        Returns
        -------
        None
            This method does not return a value.
        """
        other_var: contextvars.ContextVar[str] = contextvars.ContextVar(
            "other_var", default="original",
        )
        other_var.set("modified")

        token = ScopedContext.setCurrentScope("scope_value")
        ScopedContext.reset(token)

        self.assertIsNone(ScopedContext.getCurrentScope())
        self.assertEqual(other_var.get(), "modified")

    # ------------------------------------------------------------------
    # Context isolation
    # ------------------------------------------------------------------

    def testContextIsolationBetweenCopiedContexts(self) -> None:
        """
        Test that scope changes in a copied context do not affect the parent context.

        Uses contextvars.copy_context() to simulate the isolation that occurs
        when spawning coroutines or threads: the nested context inherits the
        parent scope but mutations remain local.

        Returns
        -------
        None
            This method does not return a value.
        """
        parent_scope = {"ctx": "parent"}
        ScopedContext.setCurrentScope(parent_scope)

        ctx = contextvars.copy_context()
        child_scope_seen: list[object] = []

        def run_in_child() -> None:
            """Run the copied context and record its active scope.

            Returns
            -------
            None
                Completes the operation described above.
            """
            child_scope_seen.append(ScopedContext.getCurrentScope())
            ScopedContext.setCurrentScope({"ctx": "child"})

        ctx.run(run_in_child)

        # Child inherited parent's scope at copy time.
        self.assertIs(child_scope_seen[0], parent_scope)
        # Parent context is unchanged after child mutated its own copy.
        self.assertIs(ScopedContext.getCurrentScope(), parent_scope)

    def testMultipleSetAndResetCycles(self) -> None:
        """
        Test multiple successive set/reset cycles produce correct scope values.

        Verifies that tokens remain valid across interleaved set and reset
        operations and that each reset correctly restores the corresponding
        prior state.

        Returns
        -------
        None
            This method does not return a value.
        """
        token_a = ScopedContext.setCurrentScope("scope_1")
        token_b = ScopedContext.setCurrentScope("scope_2")
        token_c = ScopedContext.setCurrentScope("scope_3")

        self.assertEqual(ScopedContext.getCurrentScope(), "scope_3")
        ScopedContext.reset(token_c)
        self.assertEqual(ScopedContext.getCurrentScope(), "scope_2")
        ScopedContext.reset(token_b)
        self.assertEqual(ScopedContext.getCurrentScope(), "scope_1")
        ScopedContext.reset(token_a)
        self.assertIsNone(ScopedContext.getCurrentScope())
