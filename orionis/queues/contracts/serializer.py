from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orionis.queues.entities.envelope import JobEnvelope
    from orionis.queues.job import BaseJob

class IJobSerializer(ABC):
    """Declare explicit state serialization and trusted job registration."""

    __slots__ = ()

    @abstractmethod
    def register(self, job_type: type[BaseJob]) -> None:
        """
        Register an application-trusted concrete job class.

        Parameters
        ----------
        job_type : type[BaseJob]
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
        job : BaseJob
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
        BaseJob
            Job whose handle method can receive DI services.
        """

    @abstractmethod
    def encodeEnvelope(self, envelope: JobEnvelope) -> bytes:
        """
        Encode a versioned immutable envelope.

        Parameters
        ----------
        envelope : JobEnvelope
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
        JobEnvelope
            Validated immutable execution data.
        """
