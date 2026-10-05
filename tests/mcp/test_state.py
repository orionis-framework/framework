import base64
from dataclasses import replace
import msgspec
from orionis.auth.context.context import AuthenticationContext
from orionis.auth.contracts.authenticatable import IAuthenticatable
from orionis.container.container import Container
from orionis.container.context.scope import ScopedContext
from orionis.encrypter.encrypter import Encrypter
from orionis.mcp.context import McpRequest
from orionis.mcp.exceptions import McpInvalidParams
from orionis.mcp.state import McpState
from orionis.test import TestCase

class _App(Container):
    """Provide real container lifetimes and deterministic test encryption config."""

    def config(self, key, default=None):
        """Return isolated configuration without bootstrapping unrelated providers.

        Parameters
        ----------
        key : object
            Value supplied for ``key``.
        default : object
            Value supplied for ``default``.

        Returns
        -------
        object
            Return the result produced by ``config``.
        """
        return {"app.key": b"1" * 32, "app.cipher": "AES-256-GCM"}.get(key, default)

class _Identity(IAuthenticatable):
    """An application identity using Orionis' actual authentication contract."""

    def __init__(self, identifier) -> None:
        """Retain the exact identifier type.

        Parameters
        ----------
        identifier : object
            Value supplied for ``identifier``.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.identifier = identifier

    def getAuthIdentifierName(self):
        """Return the application identifier attribute.

        Returns
        -------
        str
            Return the result produced by ``getAuthIdentifierName``.
        """
        return "identifier"

    def getAuthIdentifier(self):
        """Return the native identifier without string coercion.

        Returns
        -------
        object
            Return the result produced by ``getAuthIdentifier``.
        """
        return self.identifier

    def getAuthPassword(self):
        """Passwords are outside this test's authentication path.

        Returns
        -------
        str
            Return the result produced by ``getAuthPassword``.
        """
        return ""

class TestMcpState(TestCase):
    """State must authenticate across workers without ambient session storage."""

    def setUp(self):
        """Isolate framework scope and construct two independent native encrypters.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        self.instances = dict(Container._instances)
        self.scope = ScopedContext.setCurrentScope(None)
        self.app = _App()
        self.encrypter = Encrypter(self.app)
        self.state = McpState(self.app, self.encrypter)
        self.worker = McpState(self.app, Encrypter(self.app))
        self.request = McpRequest(
            id=1,
            method="tools/call",
            server_id="app.ai.Server",
            arguments={"amount": 10},
            params={"name": "transfer"},
            authentication=AuthenticationContext(
                _Identity(7),
                guard="api",
                credential_id="credential-one",
            ),
        )

    def tearDown(self):
        """Restore the test runner's container and scope state.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        Container._instances.clear()
        Container._instances.update(self.instances)
        ScopedContext.reset(self.scope)

    def test_cross_worker_retry_uses_fresh_id(self):
        """Only stable request context is bound; retry IDs and metadata may differ.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        token = self.state.seal(self.request, {"step": 1, "nullable": None})
        retry = replace(
            self.request,
            id="retry",
            request_state=token,
            meta={"traceparent": "new-trace"},
        )
        self.assertEqual(self.worker.open(retry), {"step": 1, "nullable": None})

    def test_request_server_and_principal_binding(self):
        """Prevent other identities, credentials, methods or servers reusing state.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        token = self.state.seal(self.request, {"approved": True})
        retry = replace(self.request, request_state=token)
        variants = (
            {"server_id": "app.ai.OtherServer"},
            {"arguments": {"amount": 20}},
            {"params": {"name": "other"}},
            {"method": "prompts/get"},
            {
                "authentication": AuthenticationContext(
                    _Identity("7"),
                    guard="api",
                    credential_id="credential-one",
                ),
            },
            {
                "authentication": AuthenticationContext(
                    _Identity(7),
                    guard="api",
                    credential_id="credential-two",
                ),
            },
            {
                "authentication": AuthenticationContext(
                    _Identity(7),
                    guard="web",
                    credential_id="credential-one",
                ),
            },
        )
        for changes in variants:
            with self.subTest(changes=changes), self.assertRaises(McpInvalidParams): # NOSONAR # noqa: E501
                self.worker.open(replace(retry, **changes))

    def test_expiry_and_wrong_purpose(self):
        """Reject authenticated envelopes that are stale or intended for another API.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        token = self.state.seal(self.request, {"step": 1})
        payload = msgspec.json.decode(self.encrypter.decrypt(token))
        for changes in ({"expires": 1}, {"purpose": "other"}, {"expires": True}):
            altered = self.encrypter.encrypt(
                msgspec.json.encode({**payload, **changes}).decode(),
            )
            with self.subTest(changes=changes), self.assertRaises(McpInvalidParams): # NOSONAR # noqa: E501
                self.worker.open(replace(self.request, request_state=altered))

    def test_tamper_and_cipher_downgrade(self):
        """Verify native AEAD authentication and configured cipher enforcement.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        token = self.state.seal(self.request, {"step": 1})
        envelope = msgspec.json.decode(base64.b64decode(token))
        ciphertext = bytearray(base64.b64decode(envelope["value"]))
        ciphertext[0] ^= 1
        for changes in (
            {"value": base64.b64encode(ciphertext).decode()},
            {"cipher": "AES-256-CBC", "tag": None},
            {"tag": None},
        ):
            altered = base64.b64encode(
                msgspec.json.encode({**envelope, **changes}),
            ).decode()
            with self.subTest(changes=changes), self.assertRaises(McpInvalidParams): # NOSONAR # noqa: E501
                self.worker.open(replace(self.request, request_state=altered))

    def test_invalid_ttl_and_missing_server_context(self):
        """Fail clearly before sealing unbound or unexpectedly long-lived state.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """
        for ttl in (0, -1, True):
            with self.subTest(ttl=ttl), self.assertRaises(ValueError):
                self.state.seal(self.request, {}, ttl=ttl)
        with self.assertRaises(ValueError): # NOSONAR
            self.state.seal(replace(self.request, server_id=""), {})

    def test_cbc_is_not_accepted_for_mrtr_state(self):
        """The native framework may support CBC while MCP state requires integrity.

        Returns
        -------
        None
            Complete the documented checks or setup without a return value.
        """

        class _CbcApp(_App):
            def config(self, key, default=None):
                """Select the framework's unauthenticated cipher for this regression.

                Parameters
                ----------
                key : object
                    Value supplied for ``key``.
                default : object
                    Value supplied for ``default``.

                Returns
                -------
                object
                    Return the result produced by ``config``.
                """
                return (
                    "AES-256-CBC"
                    if key == "app.cipher"
                    else super().config(key, default)
                )

        app = _CbcApp()
        with self.assertRaises(ValueError): # NOSONAR
            McpState(app, Encrypter(app))
