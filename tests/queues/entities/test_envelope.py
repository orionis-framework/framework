from uuid import uuid4
import msgspec
from orionis.queues.entities.envelope import JobEnvelope
from orionis.queues.exceptions import QueueConfigurationError, QueuePayloadError
from orionis.queues.serializer import JobSerializer
from orionis.test import TestCase


def envelope_options() -> dict[str, object]:
    """Build valid immutable options for envelope validation tests.

    Returns
    -------
    dict[str, object]
        Independent options with a valid job UUID.
    """
    return {
        "id": str(uuid4()), "job": "app.jobs.mail:WelcomeJob",
        "payload": b"state", "connection": "database", "queue": "emails",
        "max_tries": 3, "timeout": 2.0, "backoff": (0.01, 0.02),
    }


class TestJobEnvelope(TestCase):
    def testImmutableWireRoundTrip(self) -> None:
        """Preserve immutable dispatch options independently of reservation state.

        Returns
        -------
        None
            Verify frozen fields and the exact versioned wire representation.
        """
        envelope = JobEnvelope(**envelope_options())
        serializer = JobSerializer()
        payload = serializer.encodeEnvelope(envelope)
        self.assertEqual(serializer.decodeEnvelope(payload), envelope)
        self.assertNotIn("attempts", msgspec.json.decode(payload))
        with self.assertRaises(AttributeError):
            envelope.queue = "changed"

    def testInvalidExecutionOptionsFailExplicitly(self) -> None:
        """Reject unsupported versions, routing, durations, and attempt budgets.

        Returns
        -------
        None
            Verify corrupted execution configuration is never accepted.
        """
        for key, value in (
            ("version", 2), ("id", "broken"), ("job", "broken"),
            ("payload", "not bytes"), ("connection", "../connection"),
            ("queue", "jobs:reserved"), ("max_tries", 0), ("max_tries", True),
            ("timeout", -1), ("timeout", float("nan")),
            ("backoff", ()), ("backoff", (-1,)),
            ("retry_until", float("inf")),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(
                (QueuePayloadError, QueueConfigurationError),
            ):
                JobEnvelope(**{**envelope_options(), key: value})

    def testCorruptEnvelopeDataFailsExplicitly(self) -> None:
        """Reject malformed JSON and extra backend fields in immutable envelopes.

        Returns
        -------
        None
            Verify strict decoding rejects corrupt persistent wire data.
        """
        serializer = JobSerializer()
        for payload in (
            b"{", b"{}", b"[]",
            msgspec.json.encode({**envelope_options(), "attempts": 1}),
            msgspec.json.encode({**envelope_options(), "timeout": "60"}),
        ):
            with self.subTest(payload=payload), self.assertRaises(QueuePayloadError):
                serializer.decodeEnvelope(payload)
