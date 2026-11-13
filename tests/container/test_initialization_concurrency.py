# ruff: noqa: PT009, SLF001
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Protect singleton state from overlapping container initializers."""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor

from orionis.container.container import Container
from orionis.container.context.scope import ScopedContext
from orionis.test import TestCase


class _Dependency:
    """Identify a binding published by the second construction caller."""


class TestInitializationConcurrency(TestCase):
    """Exercise first-time container construction from independent threads."""

    async def testPreservesBindingsDuringConcurrentInitialization(self) -> None:
        """Initialize singleton state once before exposing it to another caller."""
        first_assignment = threading.Event()
        second_finished = threading.Event()
        assignment_lock = threading.Lock()

        class ConcurrentContainer(Container):
            """Pause the first initialization at its first state assignment."""

            def __setattr__(self, name: str, value: object) -> None:
                """Allow another constructor to overlap an unfinished initializer.

                Parameters
                ----------
                name : str
                    Attribute assigned by the real container initializer.
                value : object
                    Value forwarded unchanged to the real instance.

                Returns
                -------
                None
                    This method does not return a value.
                """
                if name == "_deferred_providers":
                    with assignment_lock:
                        first = not first_assignment.is_set()
                        first_assignment.set()
                    if first:
                        # A serialized second initializer cannot finish until
                        # this deadline releases the first constructor.
                        second_finished.wait(timeout=5)
                super().__setattr__(name, value)

        self.addCleanup(Container._instances.pop, ConcurrentContainer, None)

        def construct(*, register: bool) -> Container:
            """Construct the real container outside the test runner's scope.

            Parameters
            ----------
            register : bool
                Whether to publish a service after construction completes.

            Returns
            -------
            Container
                Fully initialized singleton returned to this caller.
            """
            token = ScopedContext.setCurrentScope(None)
            try:
                container = ConcurrentContainer()
                if register:
                    container.instance(_Dependency, _Dependency())
                return container
            finally:
                ScopedContext.reset(token)
                if register:
                    second_finished.set()

        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(construct, register=False)
            self.assertTrue(await asyncio.to_thread(first_assignment.wait, 5))
            second = executor.submit(construct, register=True)
            first_container = await asyncio.wait_for(
                asyncio.wrap_future(first),
                timeout=10,
            )
            second_container = await asyncio.wait_for(
                asyncio.wrap_future(second),
                timeout=10,
            )

        self.assertIs(first_container, second_container)
        self.assertTrue(first_container.bound(_Dependency))
