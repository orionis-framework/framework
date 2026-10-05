import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, cast, get_type_hints
import msgspec
from orionis.auth.contracts.context import IAuthenticationContext
from orionis.http.contracts.request import IRequest
from orionis.http.request import Request
from orionis.mcp.context import McpRequest

if TYPE_CHECKING:
    from collections.abc import Callable
    from orionis.container.contracts.container import IContainer

@dataclass(frozen=True, slots=True)
class _Parameter:
    """One compile-time classified argument, with no request references."""

    name: str
    source: Literal[
        "payload",
        "request",
        "authentication",
        "http",
        "dependency",
        "default",
        "argument",
        "uri",
    ]
    value: object
    positional: bool

def _classify(
    parameter: inspect.Parameter,
    annotation: object,
    payload_type: object,
    argument_names: tuple[str, ...],
    uri_names: tuple[str, ...],
) -> _Parameter:
    """
    Assign one trusted source to an argument before accepting requests.

    Parameters
    ----------
    parameter : inspect.Parameter
        Value supplied for ``parameter``.
    annotation : object
        Native type annotation to inspect or validate.
    payload_type : object
        Value supplied for ``payload_type``.
    argument_names : tuple[str, ...]
        Value supplied for ``argument_names``.
    uri_names : tuple[str, ...]
        Value supplied for ``uri_names``.

    Returns
    -------
    _Parameter
        Result of the operation described above.
    """
    source = "dependency"
    value = annotation
    if payload_type is not None and annotation == payload_type:
        source = "payload"
    elif annotation is McpRequest:
        source = "request"
    elif annotation is IAuthenticationContext:
        source = "authentication"
    elif annotation in (Request, IRequest):
        source = "http"
    elif parameter.name in argument_names and annotation is str:
        source, value = "argument", parameter.default
    elif parameter.name in uri_names:
        source, value = "uri", (annotation, parameter.default)
    elif isinstance(annotation, type) and issubclass(annotation, msgspec.Struct):
        message = (
            f"Schema parameter {parameter.name!r} is not the declared MCP payload."
        )
        raise TypeError(message)
    elif parameter.default is not inspect.Parameter.empty:
        source, value = "default", parameter.default
    elif not isinstance(annotation, type) or annotation.__module__ in (
        "builtins",
        "typing",
    ):
        message = (
            f"Cannot bind MCP handler parameter {parameter.name!r}; "
            "annotate a payload or dependency."
        )
        raise TypeError(message)
    return _Parameter(
        parameter.name, source, value, parameter.kind is parameter.POSITIONAL_ONLY,
    )

@dataclass(frozen=True, slots=True)
class McpInvoker:
    """A reusable unbound handler plan; payloads never become keyword mappings."""

    function: Callable[..., object]
    parameters: tuple[_Parameter, ...]
    receiver: Literal["instance", "class", "none"]

    @classmethod
    def compile(
        cls,
        definition: type,
        method: str,
        payload_type: object = None,
        *,
        argument_names: tuple[str, ...] = (),
        uri_names: tuple[str, ...] = (),
    ) -> McpInvoker:
        """
        Resolve annotations and classify all parameters once during boot.

        Parameters
        ----------
        definition : type
            Class declaration whose metadata is being inspected.
        method : str
            Value supplied for ``method``.
        payload_type : object
            Value supplied for ``payload_type``.
        argument_names : tuple[str, ...]
            Value supplied for ``argument_names``.
        uri_names : tuple[str, ...]
            Value supplied for ``uri_names``.

        Returns
        -------
        McpInvoker
            Result of the operation described above.
        """
        descriptor = inspect.getattr_static(definition, method)
        receiver = "instance"
        if isinstance(descriptor, staticmethod):
            function, receiver = descriptor.__func__, "none"
        elif isinstance(descriptor, classmethod):
            function, receiver = descriptor.__func__, "class"
        else:
            function = descriptor
        if not inspect.isfunction(function):
            message = f"MCP {definition.__name__}.{method} must be a regular method."
            raise TypeError(message)
        hints = get_type_hints(
            function, localns={**vars(definition), definition.__name__: definition},
        )
        parameters = tuple(inspect.signature(function).parameters.values())
        if receiver != "none":
            parameters = parameters[1:]
        if any(
            item.kind in (item.VAR_POSITIONAL, item.VAR_KEYWORD) for item in parameters
        ):
            message = "MCP handlers cannot accept variadic arguments."
            raise TypeError(message)
        plan = tuple(
            _classify(
                item,
                hints.get(item.name, item.annotation),
                payload_type,
                argument_names,
                uri_names,
            )
            for item in parameters
        )
        if sum(item.source == "payload" for item in plan) > 1:
            message = "An MCP handler can receive at most one typed payload."
            raise TypeError(message)
        return cls(function, plan, receiver)

    async def invoke(
        self,
        instance: object,
        app: IContainer,
        request: McpRequest,
        payload: object = msgspec.UNSET,
    ) -> object:
        """
        Inject trusted context/services while preserving generator results.

        Parameters
        ----------
        instance : object
            Instance supplying values or receiving the invocation.
        app : IContainer
            Application container supplying configuration and dependencies.
        request : McpRequest
            Current request and its trusted execution context.
        payload : object
            Input payload supplied for conversion or processing.

        Returns
        -------
        object
            Result of the operation described above.
        """
        positional: list[object] = []
        keyword: dict[str, object] = {}
        if self.receiver != "none":
            positional.append(
                instance if self.receiver == "instance" else type(instance),
            )
        for parameter in self.parameters:
            value = await self._value(parameter, app, request, payload)
            if parameter.positional:
                positional.append(value)
            else:
                keyword[parameter.name] = value
        result = self.function(*positional, **keyword)
        return await result if inspect.isawaitable(result) else result

    @staticmethod
    async def _value(
        parameter: _Parameter,
        app: IContainer,
        request: McpRequest,
        payload: object,
    ) -> object:
        """
        Resolve the trusted source chosen at compile time.

        Parameters
        ----------
        parameter : _Parameter
            Value supplied for ``parameter``.
        app : IContainer
            Application container supplying configuration and dependencies.
        request : McpRequest
            Current request and its trusted execution context.
        payload : object
            Input payload supplied for conversion or processing.

        Returns
        -------
        object
            Result of the operation described above.
        """
        if parameter.source in ("payload", "argument", "uri"):
            return McpInvoker._clientValue(parameter, request, payload)
        match parameter.source:
            case "request":
                return request
            case "authentication":
                return request.authentication
            case "http":
                if request.native_request is None:
                    message = (
                        "HTTP Request injection is unavailable on the STDIO transport."
                    )
                    raise TypeError(message)
                return request.native_request
            case "default":
                return parameter.value
            case _:
                return await app.make(cast("type", parameter.value))

    @staticmethod
    def _clientValue(
        parameter: _Parameter, request: McpRequest, payload: object,
    ) -> object:
        """
        Read only parameters explicitly declared as client-controlled input.

        Parameters
        ----------
        parameter : _Parameter
            Value supplied for ``parameter``.
        request : McpRequest
            Current request and its trusted execution context.
        payload : object
            Input payload supplied for conversion or processing.

        Returns
        -------
        object
            Result of the operation described above.
        """
        match parameter.source:
            case "payload":
                if payload is msgspec.UNSET:
                    message = "A validated MCP payload is required by this handler."
                    raise TypeError(message)
                return payload
            case "argument":
                value = request.arguments.get(parameter.name, parameter.value)
                if value is inspect.Parameter.empty:
                    message = f"Missing prompt argument {parameter.name!r}."
                    raise ValueError(message)
                return value
            case "uri":
                annotation, default = cast("tuple[object, object]", parameter.value)
                value = request.uri_variables.get(parameter.name, default)
                if value is inspect.Parameter.empty:
                    message = f"Missing URI template argument {parameter.name!r}."
                    raise ValueError(message)
                return msgspec.convert(value, type=annotation)
        message = "Invalid compiled client parameter source."
        raise RuntimeError(message)
