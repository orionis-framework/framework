# ruff: noqa: PLC0415, PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Keep runtime reflection annotations and intentionally deferred imports.
import inspect
from typing import get_type_hints
from orionis.queues.context import FailureCallback, JobContext
from orionis.queues.contracts.driver import IQueueDriver
from orionis.queues.contracts.failed_repository import IFailedJobRepository
from orionis.queues.contracts.job import IJob
from orionis.queues.contracts.manager import IQueueManager
from orionis.queues.contracts.serializer import IJobSerializer
from orionis.queues.contracts.worker import IWorker
from orionis.queues.drivers.database import DatabaseQueueDriver
from orionis.queues.drivers.redis import RedisQueueDriver
from orionis.queues.drivers.sync import SyncQueueDriver
from orionis.queues.failed.repository import DatabaseFailedJobRepository
from orionis.queues.manager import QueueManager
from orionis.queues.pending import PendingDispatch
from orionis.queues.serializer import JobSerializer
from orionis.queues.types import DispatchCallback
from orionis.queues.worker import FailedResolver, Worker, WorkerOptions
from orionis.test import TestCase

_CONTRACTS = (
    IQueueDriver,
    IFailedJobRepository,
    IJob,
    IQueueManager,
    IJobSerializer,
    IWorker,
)


class TestQueueContracts(TestCase):
    def testRuntimeAnnotationsResolveWithoutCallerNamespaces(self) -> None:
        """Resolve public queue types without injecting missing module globals.

        Returns
        -------
        None
            No return value.
        """
        for owner in (
            *_CONTRACTS,
            DatabaseQueueDriver,
            RedisQueueDriver,
            SyncQueueDriver,
            DatabaseFailedJobRepository,
            QueueManager,
            JobSerializer,
            Worker,
            WorkerOptions,
            PendingDispatch,
            JobContext,
        ):
            with self.subTest(owner=owner.__name__):
                get_type_hints(owner)
            for name, member in vars(owner).items():
                method = (
                    member.__func__
                    if isinstance(member, (classmethod, staticmethod))
                    else member
                )
                if inspect.isfunction(method) and name != "__annotate_func__":
                    with self.subTest(owner=owner.__name__, method=name):
                        get_type_hints(method)
        for alias in (FailureCallback, DispatchCallback, FailedResolver):
            with self.subTest(alias=alias.__name__):
                self.assertIsNotNone(alias.__value__)

    def testAbstractContractsHaveEmptySlots(self) -> None:
        """Declare significant queue services as abstract contracts with empty slots.

        Returns
        -------
        None
            Verify all contracts expose abstract operations.
        """
        for contract in _CONTRACTS:
            with self.subTest(contract=contract):
                self.assertTrue(inspect.isabstract(contract))
                self.assertEqual(contract.__slots__, ())

    def testImplementationsSatisfyContracts(self) -> None:
        """Implement every declared operation without leaving abstract services.

        Returns
        -------
        None
            Verify each runtime implementation is concrete and uses slots.
        """
        for implementation, contract in (
            (DatabaseQueueDriver, IQueueDriver),
            (RedisQueueDriver, IQueueDriver),
            (SyncQueueDriver, IQueueDriver),
            (DatabaseFailedJobRepository, IFailedJobRepository),
            (QueueManager, IQueueManager),
            (JobSerializer, IJobSerializer),
            (Worker, IWorker),
        ):
            with self.subTest(implementation=implementation):
                self.assertTrue(issubclass(implementation, contract))
                self.assertFalse(inspect.isabstract(implementation))
                self.assertIn("__slots__", implementation.__dict__)

    def testPublicFacadeAndPackageExports(self) -> None:
        """Expose canonical facade and job classes through existing package exports.

        Returns
        -------
        None
            Verify imports resolve to their defining classes.
        """
        from orionis.queues import BaseJob, JobContext, JobEnvelope, PendingDispatch
        from orionis.queues.context import JobContext as DirectContext
        from orionis.queues.entities.envelope import JobEnvelope as DirectEnvelope
        from orionis.queues.job import BaseJob as DirectJob
        from orionis.queues.pending import PendingDispatch as DirectPending
        from orionis.support.facades import Queue
        from orionis.support.facades.queue import Queue as DirectQueue

        self.assertIs(BaseJob, DirectJob)
        self.assertIs(JobContext, DirectContext)
        self.assertIs(JobEnvelope, DirectEnvelope)
        self.assertIs(PendingDispatch, DirectPending)
        self.assertIs(Queue, DirectQueue)
        self.assertIs(Queue.getFacadeAccessor(), IQueueManager)
