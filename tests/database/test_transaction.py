# ruff: noqa: PT009, PT027
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
from __future__ import annotations
from orionis.database.contracts.transaction import ITransaction
from orionis.database.exceptions import TransactionException
from orionis.database.transaction import Transaction
from orionis.test import TestCase


class _FakeConnection:
    """Fake connection recording the transaction control calls it receives."""

    def __init__(self, *, fail_begin: bool = False) -> None:
        """
        Initialize the fake connection.

        Parameters
        ----------
        fail_begin : bool, optional
            Whether ``begin`` should raise instead of succeeding.

        Returns
        -------
        None
            No return value.
        """
        self.calls: list[str] = []
        self._fail_begin = fail_begin

    async def begin(self) -> None:
        """Record the call and optionally simulate a failure to start.

        Returns
        -------
        None
            No return value.

        Raises
        ------
        TransactionException
            Raised by this helper to exercise the failure path.
        """
        self.calls.append("begin")
        if self._fail_begin:
            error_msg = "Unable to begin transaction."
            raise TransactionException(error_msg)

    async def commit(self) -> None:
        """Record the commit call.

        Returns
        -------
        None
            No return value.
        """
        self.calls.append("commit")

    async def rollback(self) -> None:
        """Record the rollback call.

        Returns
        -------
        None
            No return value.
        """
        self.calls.append("rollback")


class TestTransaction(TestCase):
    async def testEnterBeginsTransactionAndReturnsItself(self) -> None:
        """Begin the transaction and yield the transaction itself.

        Validates the entry point of the async context manager.

        Returns
        -------
        None
            No return value.
        """
        connection = _FakeConnection()
        transaction = Transaction(connection)
        entered = await transaction.__aenter__()
        self.assertIs(entered, transaction)
        self.assertEqual(connection.calls, ["begin"])
        self.assertFalse(await transaction.__aexit__(None, None, None))
        self.assertEqual(connection.calls, ["begin", "commit"])

    async def testCleanExitCommitsTransaction(self) -> None:
        """Commit the transaction when the block exits without error.

        Validates the successful path of the async context manager.

        Returns
        -------
        None
            No return value.
        """
        connection = _FakeConnection()
        async with Transaction(connection):
            pass
        self.assertEqual(connection.calls, ["begin", "commit"])

    async def testExceptionExitRollsBackTransaction(self) -> None:
        """Roll back the transaction when an exception escapes the block.

        Validates the failure path of the async context manager.

        Returns
        -------
        None
            No return value.

        """
        connection = _FakeConnection()
        error = RuntimeError("boom")
        with self.assertRaises(RuntimeError) as caught:
            async with Transaction(connection):
                raise error
        self.assertIs(caught.exception, error)
        self.assertEqual(connection.calls, ["begin", "rollback"])

    async def testAexitReturnsFalseOnException(self) -> None:
        """Return False from __aexit__ so exceptions keep propagating.

        Validates the direct contract of __aexit__ regardless of the
        surrounding ``async with`` statement.

        Returns
        -------
        None
            No return value.
        """
        connection = _FakeConnection()
        transaction = Transaction(connection)
        await transaction.__aenter__()
        error = RuntimeError("boom")
        result = await transaction.__aexit__(RuntimeError, error, None)
        self.assertFalse(result)
        self.assertEqual(connection.calls, ["begin", "rollback"])

    async def testBeginFailurePreventsCommitOrRollback(self) -> None:
        """Propagate a failure to start without attempting to finalize it.

        Validates that a broken ``begin`` never triggers a spurious
        commit or rollback call.

        Returns
        -------
        None
            No return value.
        """
        connection = _FakeConnection(fail_begin=True)
        with self.assertRaises(TransactionException):
            async with Transaction(connection):
                pass
        self.assertEqual(connection.calls, ["begin"])

    async def testTransactionSatisfiesItsContract(self) -> None:
        """Implement the ITransaction contract.

        Validates that Transaction is usable wherever ITransaction is
        expected, such as the Connection.transaction() factory.

        Returns
        -------
        None
            No return value.
        """
        transaction = Transaction(_FakeConnection())
        self.assertIsInstance(transaction, ITransaction)
