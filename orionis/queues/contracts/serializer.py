# ruff: noqa: TC001
# Keep public contract annotations available for runtime inspection.
"""Declare explicit state serialization and trusted job registration."""

from abc import ABC, abstractmethod
from orionis.queues.entities.envelope import JobEnvelope
from orionis.queues.job import BaseJob


class IJobSerializer(ABC):
    """Declare explicit state serialization and trusted job registration."""

    __slots__ = ()
    """Declare that this class introduces no additional instance slots."""

    @abstractmethod
    def register(self, job_type: type[BaseJob]) -> None:
        """
        Register an application-trusted concrete job class.

        Parameters
        ----------
        job_type : type[orionis.queues.BaseJob]
            Class supplied by trusted application code.

        Returns
        -------
        None
            Cache the class and its persistent field metadata.
        """

    @abstractmethod
    def encode(self, job: BaseJob) -> tuple[str, bytes]:
        """
        Serialize only the job's declared persistent fields.

        Parameters
        ----------
        job : orionis.queues.BaseJob
            Application job instance.

        Returns
        -------
        tuple[str, bytes]
            Stable identity and MessagePack state.
        """

    @abstractmethod
    def decode(self, identity: str, payload: bytes) -> BaseJob:
        """
        Restore a registered job without constructing dependencies.

        Parameters
        ----------
        identity : str
            Identity present in the trusted registry.
        payload : bytes
            Serialized persistent state.

        Returns
        -------
        orionis.queues.BaseJob
            Job whose handle method can receive DI services.
        """

    @abstractmethod
    def encodeEnvelope(self, envelope: JobEnvelope) -> bytes:
        """
        Encode a versioned immutable envelope.

        Parameters
        ----------
        envelope : orionis.queues.JobEnvelope
            Immutable data to persist.

        Returns
        -------
        bytes
            The JSON wire representation.
        """

    @abstractmethod
    def decodeEnvelope(self, payload: bytes) -> JobEnvelope:
        """
        Validate a stored envelope before execution.

        Parameters
        ----------
        payload : bytes
            Untrusted JSON wire data.

        Returns
        -------
        orionis.queues.JobEnvelope
            Validated immutable execution data.
        """
