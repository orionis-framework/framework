import asyncio
from dataclasses import replace
from typing import ClassVar
import msgspec
from orionis.http.exceptions.response_validation import ResponseValidationException
from orionis.http.responses import JSONResponse, Response
from orionis.schemas.constraints import GreaterThanOrEqual  # noqa: TC001
from orionis.schemas.exceptions.validation import ValidationException
from orionis.schemas.fields import Field  # noqa: TC001
from orionis.schemas.rule import Rule
from orionis.schemas.schema import Schema
from orionis.schemas.validator import Schema as Validator
from orionis.test import TestCase
from tests.http.test_kernel import (
    _StubRsgiProtocol,
    _StubRsgiScope,
    boot_kernel,
    dispatch,
    make_route,
)
from tests.http.test_support import replace_attribute

class _Ready(Rule):
    """Record asynchronous business validation of an output field."""

    __code__ = "ready"
    __message__ = "State must be ready."
    calls: ClassVar[list[object]] = []

    async def enforce(self, _field: str, value: object, _instance: object) -> bool:
        """
        Record the output value after yielding to the event loop.

        Parameters
        ----------
        _field : str
            Unused field name.
        value : object
            Output value to record and check.
        _instance : object
            Unused schema instance.

        Returns
        -------
        bool
            Whether the recorded value equals ``"ready"``.
        """
        await asyncio.sleep(0)
        self.calls.append(value)
        return value == "ready"

class _Output(Schema):
    quantity: Field[int, GreaterThanOrEqual(1)]
    state: Field[str, _Ready()] = "ready"

class _NestedOutput(Schema):
    items: list[_Output]

class _OutputController:
    """Return an output contract from an ordinary controller method."""

    def show(self) -> _Output:
        """
        Produce a valid schema for automatic output validation.

        Returns
        -------
        _Output
            Schema with a positive quantity and the default ready state.
        """
        return _Output(quantity=2)

def invalid_constraint() -> _Output:
    """
    Construct an output that violates its native quantity constraint.

    Returns
    -------
    _Output
        Schema containing a quantity of zero.
    """
    return _Output(quantity=0)

def invalid_type() -> _Output:
    """
    Construct an output that violates its declared quantity type.

    Returns
    -------
    _Output
        Schema containing a string in the integer field.
    """
    return _Output(quantity="bad")

def invalid_rule() -> object:
    """
    Return a schema whose state fails its asynchronous rule.

    Returns
    -------
    _Output
        Schema containing the rejected pending state.
    """
    return _Output(quantity=2, state="pending")

def mutated_nested() -> _NestedOutput:
    """
    Return a nested schema mutated after construction.

    Returns
    -------
    _NestedOutput
        Container holding a child with an invalid quantity.
    """
    item = _Output(quantity=2)
    item.quantity = 0
    return _NestedOutput(items=[item])

def annotated_mapping() -> _Output:
    """
    Return a mapping to test validation based on the runtime value.

    Returns
    -------
    dict[str, str]
        Mapping deliberately incompatible with the return annotation.
    """
    return {"quantity": "unvalidated"}

def explicit_response() -> Response:
    """
    Wrap an invalid schema in an explicit JSON response.

    Returns
    -------
    Response
        Response whose content bypasses direct-schema output validation.
    """
    return JSONResponse(_Output(quantity=0))

class TestSchemaResponses(TestCase):
    """Exercise schema output validation through HTTP transport entry points."""

    async def testControllerOutputRunsRulesBeforeSerialization(self) -> None:
        """
        Validate controller outputs through both HTTP transports.

        Returns
        -------
        None
            Assert successful responses and awaited output rules.
        """
        _Ready.calls.clear()
        route = replace(
            make_route("/output", controller="_OutputController"),
            action={
                "module": __name__, "class": "_OutputController", "method": "show",
            },
        )
        kernel, _app, _responses, catch = await boot_kernel(
            routes={"GET": {"static": {"/output": route}, "dynamic": []}},
        )
        for interface in ("asgi", "rsgi"):
            response = (
                await dispatch(kernel, "/output") if interface == "asgi"
                else await kernel.handleRSGI(
                    _StubRsgiScope("/output"), _StubRsgiProtocol(),
                )
            )
            self.assertEqual(response.getStatusCode(), 200)
            self.assertEqual(
                msgspec.json.decode(response.getBody()),
                {"quantity": 2, "state": "ready"},
            )
        self.assertEqual(_Ready.calls, ["ready", "ready"])
        self.assertEqual(catch.handled, [])

    async def testInvalidOutputsAreServerErrorsForApiAndWeb(self) -> None:
        """
        Treat invalid output schemas as server errors for API and web routes.

        Returns
        -------
        None
            Assert HTTP 500 responses and preserved validation causes.
        """
        for kind in ("api", "web"):
            for handler, field, rule in (
                ("invalid_constraint", "quantity", "ge"),
                ("invalid_type", "quantity", "type"),
                ("invalid_rule", "state", "ready"),
                ("mutated_nested", "items[0].quantity", "ge"),
            ):
                with self.subTest(kind=kind, handler=handler):
                    route = replace(
                        make_route("/output", kind=kind, function=handler),
                        action={"module": __name__, "function": handler},
                    )
                    kernel, _app, _responses, catch = await boot_kernel(
                        routes={"GET": {"static": {"/output": route}, "dynamic": []}},
                    )
                    response = await dispatch(kernel, "/output")
                    self.assertEqual(response.getStatusCode(), 500)
                    self.assertEqual(
                        response.getBody(), b"The response schema is invalid.",
                    )
                    self.assertEqual(len(catch.handled), 1)
                    failure = catch.handled[0]
                    self.assertIsInstance(failure, ResponseValidationException)
                    cause = failure.__cause__
                    self.assertIsInstance(cause, ValidationException)
                    self.assertIn(
                        (field, rule),
                        [(item.field, item.rule) for item in cause.failures],
                    )

    async def testOtherResponsesNeverInvokeSchemaValidation(self) -> None:
        """
        Skip schema validation for ordinary response values.

        Returns
        -------
        None
            Assert mappings, plain structs and explicit responses bypass validation.
        """
        kernel, _app, _responses, _catch = await boot_kernel()
        calls: list[object] = []

        async def validate(payload: object, _schema: type) -> object:
            """
            Record and reject an unexpected output validation call.

            Parameters
            ----------
            payload : object
                Unexpected output value to record.
            _schema : type
                Unused validation target.

            Returns
            -------
            NoReturn
                Never return normally.

            Raises
            ------
            AssertionError
                Always, after recording the unexpected payload.
            """
            calls.append(payload)
            error_msg = "Unexpected validation"
            raise AssertionError(error_msg)

        with replace_attribute(Validator, "validate", staticmethod(validate)):
            for path in ("/api", "/dict", "/struct"):
                response = await dispatch(kernel, path)
                self.assertEqual(response.getStatusCode(), 200)
            for handler in ("annotated_mapping", "explicit_response"):
                route = replace(
                    make_route("/output", function=handler),
                    action={"module": __name__, "function": handler},
                )
                selected, _app, _responses, catch = await boot_kernel(
                    routes={"GET": {"static": {"/output": route}, "dynamic": []}},
                )
                response = await dispatch(selected, "/output")
                self.assertEqual(response.getStatusCode(), 200)
                self.assertEqual(catch.handled, [])
        self.assertEqual(calls, [])
