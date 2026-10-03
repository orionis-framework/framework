import dataclasses
import math
import msgspec
from orionis.http.websocket_message import WebSocketMessage, WebSocketMessageType
from orionis.realtime.config import RealtimeConfig
from orionis.realtime.errors import ProtocolError
from orionis.realtime.protocol import (
    Cancel, Completion, HubProtocol, Invoke, Ping, Pong, RPCErrorPayload,
)
from orionis.test import TestCase


def _frame(payload: object, protocol: str = "json") -> WebSocketMessage:
    """
    Encode one envelope using the frame kind required by its codec.

    Parameters
    ----------
    payload : object
        Envelope tested by the strict client decoder.
    protocol : str, optional
        JSON or MessagePack encoding.

    Returns
    -------
    WebSocketMessage
        Complete incoming frame.
    """
    if protocol == "json":
        return WebSocketMessage(
            type=WebSocketMessageType.TEXT,
            data=msgspec.json.encode(payload).decode("utf-8"),
        )
    return WebSocketMessage(
        type=WebSocketMessageType.BYTES, data=msgspec.msgpack.encode(payload),
    )


class TestHubProtocol(TestCase):
    """Validate version-one envelopes independently of networking and RPC."""

    def testBothCodecsDecodeInvocationDefaultsAndUnicode(self) -> None:
        """
        Keep typed invocation behavior identical for JSON and MessagePack.

        Returns
        -------
        None
            Envelope fields and optional defaults survive both codecs.
        """
        for name in ("json", "msgpack"):
            with self.subTest(name=name):
                protocol = HubProtocol(name)
                message = protocol.decode(_frame({
                    "type": "invoke", "id": "req-1", "target": "saludar",
                    "args": ["Hola 👋"], "timeout": 5,
                }, name))
                if not isinstance(message, Invoke):
                    self.fail("Expected a typed invoke envelope")
                self.assertEqual(message.args, ["Hola 👋"])
                self.assertEqual(message.kwargs, {})
                self.assertEqual(message.timeout, 5)
                empty = protocol.decode(_frame({
                    "type": "invoke", "id": "req-2", "target": "ping",
                }, name))
                if not isinstance(empty, Invoke):
                    self.fail("Expected a typed invoke envelope")
                self.assertEqual(empty.args, [])
                self.assertIsNone(empty.timeout)

    def testCompletionPreservesNullAndTypedClientError(self) -> None:
        """
        Distinguish an explicit null result from a missing completion outcome.

        Returns
        -------
        None
            Null results and safe typed errors remain distinguishable.
        """
        for name in ("json", "msgpack"):
            protocol = HubProtocol(name)
            null = protocol.decode(_frame({
                "type": "completion", "id": "s-1", "result": None,
            }, name))
            if not isinstance(null, Completion):
                self.fail("Expected a typed completion envelope")
            self.assertIsNone(null.result)
            self.assertIs(null.error, msgspec.UNSET)
            error = protocol.decode(_frame({
                "type": "completion", "id": "s-2",
                "error": {"code": "unavailable", "message": "Please retry"},
            }, name))
            if not isinstance(error, Completion):
                self.fail("Expected a typed completion envelope")
            self.assertIs(error.result, msgspec.UNSET)
            if not isinstance(error.error, RPCErrorPayload):
                self.fail("Expected a typed client error")
            self.assertEqual(error.error.code, "unavailable")

    def testPingPongAndCancelAreTyped(self) -> None:
        """
        Accept the small set of control envelopes without extra fields.

        Returns
        -------
        None
            Decoded messages carry their explicit protocol type.
        """
        protocol = HubProtocol()
        for payload, expected in (
            ({"type": "ping"}, Ping), ({"type": "pong"}, Pong),
            ({"type": "cancel", "id": "req-1"}, Cancel),
        ):
            self.assertIsInstance(protocol.decode(_frame(payload)), expected)

    def testServerOnlyAndUnknownFramesAreRejected(self) -> None:
        """
        Reject client attempts to inject server events or undefined types.

        Returns
        -------
        None
            All inbound types belong to the documented client grammar.
        """
        protocol = HubProtocol()
        for message_type in (
            "send", "ready", "stream_item", "stream_complete", "other",
        ):
            with (
                self.subTest(message_type=message_type),
                self.assertRaises(ProtocolError),
            ):
                protocol.decode(_frame({"type": message_type}))

    def testWrongFieldTypesAndUnknownFieldsAreRejected(self) -> None:
        """
        Prevent malformed shapes from reaching dispatch or pending registries.

        Returns
        -------
        None
            The strict msgspec tagged union validates every envelope shape.
        """
        cases = [
            [], None, {"id": "x"}, {"type": 1},
            {"type": "ping", "extra": True},
            {"type": "cancel", "id": 1},
            {"type": "invoke", "id": "x", "target": "ping", "args": {}},
            {"type": "invoke", "id": "x", "target": "ping", "kwargs": []},
            {"type": "invoke", "id": "x", "target": "ping", "timeout": True},
            {"type": "completion", "id": "x", "error": "error"},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ProtocolError):
                HubProtocol().decode(_frame(case))

    def testMalformedJsonAndMessagePackErrorsAreSanitized(self) -> None:
        """
        Hide decoder details and client payloads in protocol failures.

        Returns
        -------
        None
            Invalid bytes produce a stable public error.
        """
        for protocol, frame in (
            (HubProtocol(), WebSocketMessage(
                type=WebSocketMessageType.TEXT, data="{secret-token:",
            )),
            (HubProtocol("msgpack"), WebSocketMessage(
                type=WebSocketMessageType.BYTES, data=b"\xc1",
            )),
        ):
            with self.assertRaises(ProtocolError) as exc:
                protocol.decode(frame)
            self.assertEqual(str(exc.exception), "Invalid realtime message")

    def testCompletionRequiresExactlyOneOutcome(self) -> None:
        """
        Reject missing or conflicting completion outcomes.

        Returns
        -------
        None
            A client cannot provide an ambiguous future result.
        """
        for outcome in (
            {}, {"result": None, "error": {"code": "error", "message": "error"}},
            {"error": None},
        ):
            with self.subTest(outcome=outcome), self.assertRaises(ProtocolError):
                HubProtocol().decode(_frame({
                    "type": "completion", "id": "x", **outcome,
                }))

    def testBoundedIdsNamesArgumentsAndErrors(self) -> None:
        """
        Reject oversized identifiers, argument tables and error descriptions.

        Returns
        -------
        None
            All structural limits are enforced before execution.
        """
        base = {"type": "invoke", "id": "x", "target": "ping"}
        cases = [
            {**base, "id": ""}, {**base, "id": "x" * 129},
            {**base, "id": "contains space"}, {**base, "id": "control\n"},
            {**base, "target": ""}, {**base, "target": "x" * 129},
            {**base, "args": [0] * 65},
            {**base, "kwargs": {str(index): index for index in range(65)}},
            {**base, "kwargs": {"x" * 129: 1}},
            {"type": "completion", "id": "x", "error": {"code": "", "message": ""}},
            {"type": "completion", "id": "x", "error": {
                "code": "x" * 65, "message": "",
            }},
            {"type": "completion", "id": "x", "error": {
                "code": "error", "message": "x" * 1025,
            }},
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ProtocolError):
                HubProtocol().decode(_frame(case))

    def testInvocationTimeoutMustBeFiniteAndPositive(self) -> None:
        """
        Reject zero, negative and nonfinite per-invocation timeout values.

        Returns
        -------
        None
            Timeout values cannot undermine the invocation budget.
        """
        for timeout in (0, -1, math.inf, -math.inf, math.nan):
            with self.subTest(timeout=timeout), self.assertRaises(ProtocolError):
                HubProtocol("msgpack").decode(_frame({
                    "type": "invoke", "id": "x", "target": "ping", "timeout": timeout,
                }, "msgpack"))

    def testMessageLimitCountsUtf8Bytes(self) -> None:
        """
        Enforce a byte budget for both wire encodings including Unicode.

        Returns
        -------
        None
            Multibyte text cannot exceed the configured byte budget.
        """
        frame = _frame({"type": "invoke", "id": "x", "target": "ping", "args": ["👋"]})
        size = len(frame.text.encode("utf-8"))
        self.assertIsInstance(HubProtocol(max_message_size=size).decode(frame), Invoke)
        with self.assertRaises(ProtocolError) as exc:
            HubProtocol(max_message_size=size - 1).decode(frame)
        self.assertEqual(exc.exception.close_code, 1009)

    def testFrameKindMustMatchRouteCodec(self) -> None:
        """
        Require unambiguous route-selected text or binary serialization.

        Returns
        -------
        None
            Codec mismatches request an unsupported-data close.
        """
        for name, other in (("json", "msgpack"), ("msgpack", "json")):
            with self.assertRaises(ProtocolError) as exc:
                HubProtocol(name).decode(_frame({"type": "ping"}, other))
            self.assertEqual(exc.exception.close_code, 1003)

    def testEncodingOutputsTransportReadyPayloadAndSerializationErrors(self) -> None:
        """
        Reuse immutable encoded payloads and surface invalid result types.

        Returns
        -------
        None
            JSON uses strings and MessagePack uses bytes without transport coupling.
        """
        envelope = {"type": "completion", "id": "x", "result": None}
        text = HubProtocol().encode(envelope)
        binary = HubProtocol("msgpack").encode(envelope)
        self.assertIsInstance(text, str)
        if not isinstance(binary, bytes):
            self.fail("Expected a binary MessagePack envelope")
        self.assertEqual(msgspec.json.decode(text), envelope)
        self.assertEqual(msgspec.msgpack.decode(binary), envelope)
        with self.assertRaises(TypeError):
            HubProtocol().encode({"result": object()})

    def testInvalidCodecConfigurationFailsImmediately(self) -> None:
        """
        Reject undefined codec names and invalid byte budgets at startup.

        Returns
        -------
        None
            Runtime decoding is never entered with invalid configuration.
        """
        with self.assertRaises(ValueError):
            HubProtocol("unknown")
        for limit in (0, -1, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                HubProtocol(max_message_size=limit)


class TestRealtimeConfiguration(TestCase):
    """Validate immutable positive and finite realtime limits."""

    def testDefaultsAreFiniteAndFrozen(self) -> None:
        """
        Expose a slotted entity compatible with standard configuration loading.

        Returns
        -------
        None
            Entity serialization and immutability match the foundation conventions.
        """
        config = RealtimeConfig()
        self.assertEqual(config.toDict()["max_message_size"], 1024 * 1024)
        self.assertFalse(hasattr(config, "__dict__"))
        field = "max_concurrent_invocations"
        with self.assertRaises(dataclasses.FrozenInstanceError):
            setattr(config, field, 0)

    def testAllLimitsRejectBooleansZeroAndNegativeValues(self) -> None:
        """
        Prevent accidentally unlimited or boolean resource budgets.

        Returns
        -------
        None
            Each configuration field validates independently.
        """
        for field in dataclasses.fields(RealtimeConfig):
            for invalid in (True, 0, -1):
                with (
                    self.subTest(field=field.name, invalid=invalid),
                    self.assertRaises((TypeError, ValueError)),
                ):
                    RealtimeConfig(**{field.name: invalid})
        for invalid in (math.inf, math.nan):
            with self.subTest(invalid=invalid):
                with self.assertRaises(ValueError):
                    RealtimeConfig(invocation_timeout=invalid)
                with self.assertRaises(ValueError):
                    RealtimeConfig(client_result_timeout=invalid)
