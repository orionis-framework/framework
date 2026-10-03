from typing import ClassVar
import msgspec
from orionis.queues.exceptions import (
    QueueConfigurationError, QueuePayloadError, UnknownJobError,
)
from orionis.queues.job import BaseJob
from orionis.queues.serializer import JobSerializer
from orionis.test import TestCase

class StateJob(BaseJob):
    """Retain persistent state without constructing service dependencies."""

    __slots__ = ("data", "user_id")

    user_id: int

    def __init__(self, user_id: int, data: object) -> None:
        """Store the job's application-owned arguments.

        Parameters
        ----------
        user_id : int
            Persistent user identity.
        data : object
            Primitive data used by serializer tests.
        """
        self.user_id = user_id
        self.data = data

    async def handle(self) -> None:
        """Validate the persistent identity during execution.

        Returns
        -------
        None
            Reject invalid identities.
        """
        if self.user_id < 0:
            message = "Negative identity."
            raise ValueError(message)

class InheritedStateJob(StateJob):
    """Retain inherited fields alongside a single declared slot."""

    __slots__ = ("label",)

    label: str
    category: ClassVar[str] = "inherited"

class UndeclaredJob(BaseJob):
    """Expose undeclared fields to test explicit serialization requirements."""

    __slots__ = ("__dict__",)

    async def handle(self) -> None:
        """Clear temporary application state when explicitly executed.

        Returns
        -------
        None
            Remove temporary fields.
        """
        self.__dict__.clear()

class AnnotatedJob(UndeclaredJob):
    """Declare persistent fields stored in an inherited instance dictionary."""

    __slots__ = ()

    data: str
    user_id: int

class BlockingJob(BaseJob):
    """Expose a synchronous handler rejected by the async registry."""

    __slots__ = ()

    def handle(self) -> None:
        """Reject execution outside the asynchronous job contract.

        Returns
        -------
        None
            Raise a test-specific execution error.
        """
        message = "Synchronous jobs are not supported."
        raise RuntimeError(message)

class TestJobSerializer(TestCase):
    def testRoundTripPersistentFields(self) -> None:
        """Restore primitive collections, bytes, and nested tuples faithfully.

        Returns
        -------
        None
            Verify stable identity and owned reconstructed state.
        """
        serializer = JobSerializer()
        original = StateJob(42, {"items": [None, True, 2.5, b"data", (1, (2,))]})
        identity, payload = serializer.encode(original)
        restored = serializer.decode(identity, payload)
        self.assertIsInstance(restored, StateJob)
        self.assertEqual(restored.user_id, original.user_id)
        self.assertEqual(restored.data, original.data)
        self.assertIsNot(restored.data, original.data)

    def testInheritedSlotsAndClassVariables(self) -> None:
        """Collect inherited fields in order without persisting class variables.

        Returns
        -------
        None
            Verify inherited slots, field constraints, and ClassVar filtering.
        """
        serializer = JobSerializer()
        original = InheritedStateJob(7, None)
        original.label = "saved"
        identity, payload = serializer.encode(original)
        self.assertEqual(
            tuple(msgspec.msgpack.decode(payload)),
            ("data", "user_id", "label"),
        )
        restored = serializer.decode(identity, payload)
        self.assertIsInstance(restored, InheritedStateJob)
        self.assertEqual(restored.label, original.label)
        self.assertEqual(restored.user_id, original.user_id)
        self.assertIsNone(restored.data)

    def testRejectContainerSubclasses(self) -> None:
        """Reject subclasses while accepting only plain primitive containers.

        Returns
        -------
        None
            Verify type clarification does not broaden serializable state.
        """
        serializer = JobSerializer()
        for container_type, value in (
            (list, [1]),
            (tuple, (1,)),
            (dict, {"item": 1}),
        ):
            derived_type = type(
                f"Derived{container_type.__name__.title()}",
                (container_type,),
                {"__slots__": ()},
            )
            with self.assertRaises(QueuePayloadError):
                serializer.encode(StateJob(1, derived_type(value)))

    def testRestorationDoesNotRunConstructor(self) -> None:
        """Reconstruct slots independently of constructors and DI services.

        Returns
        -------
        None
            Verify a worker can restore registered fields directly.
        """
        serializer = JobSerializer()
        serializer.register(StateJob)
        identity = f"{StateJob.__module__}:{StateJob.__qualname__}"
        restored = serializer.decode(
            identity, msgspec.msgpack.encode({"user_id": 1, "data": "saved"}),
        )
        self.assertEqual(restored.data, "saved")

    def testUnknownIdentityNeverImports(self) -> None:
        """Reject unregistered payload identities without importing modules.

        Returns
        -------
        None
            Verify arbitrary types cannot be reconstructed.
        """
        with self.assertRaises(UnknownJobError):
            JobSerializer().decode("os:system", msgspec.msgpack.encode({}))

    def testRejectMalformedAndMismatchedFields(self) -> None:
        """Reject corrupt, extra, missing, and incorrectly typed persistent data.

        Returns
        -------
        None
            Verify decoding fails explicitly for every invalid shape.
        """
        serializer = JobSerializer()
        identity, _ = serializer.encode(StateJob(1, None))
        for payload in (
            b"\xc1",
            msgspec.msgpack.encode({}),
            msgspec.msgpack.encode({"user_id": 1, "data": None, "service": 2}),
            msgspec.msgpack.encode({"user_id": "1", "data": None}),
            msgspec.msgpack.encode([]),
            msgspec.msgpack.encode({"user_id": 1, "data": float("inf")}),
        ):
            with self.subTest(payload=payload), self.assertRaises(QueuePayloadError):
                serializer.decode(identity, payload)

    def testRejectObjectsAndUndeclaredState(self) -> None:
        """Reject arbitrary services, cycles, and undeclared instance fields.

        Returns
        -------
        None
            Verify jobs carry persistent data only.
        """
        serializer = JobSerializer()
        cycle = []
        cycle.append(cycle)
        for value in (object(), {1: "bad key"}, float("nan"), cycle):
            with self.subTest(value=type(value)), self.assertRaises(QueuePayloadError):
                serializer.encode(StateJob(1, value))
        undeclared = UndeclaredJob()
        undeclared.service = object()
        with self.assertRaises(QueuePayloadError):
            serializer.encode(undeclared)

    def testRejectIncomparableInstanceFields(self) -> None:
        """Reject extra fields even when a declared field is also missing.

        Returns
        -------
        None
            Verify field validation uses inclusion rather than strict ordering.
        """
        serializer = JobSerializer()
        original = AnnotatedJob()
        original.user_id = 7
        original.data = "saved"
        identity, payload = serializer.encode(original)
        restored = serializer.decode(identity, payload)
        self.assertEqual(restored.__dict__, original.__dict__)
        del original.data
        original.service = None
        with self.assertRaisesRegex(
            QueuePayloadError, "Declare all persistent job fields",
        ):
            serializer.encode(original)

    def testRejectBlockingHandlerAndAbstractJob(self) -> None:
        """Require concrete asynchronous job handlers.

        Returns
        -------
        None
            Verify registration enforces the execution contract.
        """
        for job_type in (BaseJob, BlockingJob):
            with self.subTest(job_type=job_type), self.assertRaises(
                QueueConfigurationError,
            ):
                JobSerializer().register(job_type)

    def testRejectUnknownExtensionAndLargeData(self) -> None:
        """Enforce the wire limit and reject unknown MessagePack extensions.

        Returns
        -------
        None
            Verify corrupt extension data and oversized state are rejected.
        """
        serializer = JobSerializer()
        identity, _ = serializer.encode(StateJob(1, None))
        with self.assertRaises(QueuePayloadError):
            serializer.decode(identity, b"x" * (1024 * 1024 + 1))
        payload = msgspec.msgpack.encode({
            "user_id": 1, "data": msgspec.msgpack.Ext(2, b"x"),
        })
        with self.assertRaises(QueuePayloadError):
            serializer.decode(identity, payload)
