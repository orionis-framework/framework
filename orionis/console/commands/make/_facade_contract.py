"""Read a service contract's signatures without importing application modules."""

import ast
import builtins
import keyword
import sys
from copy import deepcopy
from functools import cache
from importlib.util import resolve_name
from pathlib import Path
from textwrap import indent
from typing import TYPE_CHECKING, overload

if TYPE_CHECKING:
    from collections.abc import Iterator

type Method = ast.FunctionDef | ast.AsyncFunctionDef
"""Syntax node for a synchronous or asynchronous service method."""
_TYPE_PARAMETERS = (ast.TypeVar, ast.ParamSpec, ast.TypeVarTuple)
"""Type parameter nodes supported in a Python generic declaration."""


def _declarations(body: list[ast.stmt]) -> Iterator[ast.stmt]:
    """Include imports guarded by TYPE_CHECKING or version checks.

    Parameters
    ----------
    body
        Statements in the module or class being inspected.

    Yields
    ------
    ``ast.stmt``
        Each statement, including declarations inside conditional blocks.
    """
    for node in body:
        yield node
        if isinstance(node, ast.If):
            yield from _declarations(node.body)
            yield from _declarations(node.orelse)


class _Module:
    """Names and class declarations visible in a Python module."""

    def __init__(self, name: str, path: Path) -> None: # NOSONAR
        """
        Read the imports and classes defined by a contract module.

        Parameters
        ----------
        name
            Qualified name used to resolve relative imports.
        path
            Python source or stub file to parse.

        Returns
        -------
        None
            Record the declarations without importing the module.
        """
        self.name = name
        """Qualified name of the source module."""
        self.names: dict[str, str] = {}
        """Local imported names mapped to their qualified names."""
        self.imported_modules: dict[str, str] = {}
        """Local module names mapped to the paths needed in import statements."""
        self.classes: dict[str, ast.ClassDef] = {}
        """Class declarations indexed by their names in this module."""
        package = name if path.stem == "__init__" else name.rpartition(".")[0]
        tree = ast.parse(path.read_bytes(), filename=str(path))
        for node in _declarations(tree.body):
            if isinstance(node, ast.ImportFrom):
                origin = resolve_name("." * node.level + (node.module or ""), package)
                for alias in node.names:
                    self.names[alias.asname or alias.name] = f"{origin}.{alias.name}"
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    self.imported_modules[alias.asname or root] = alias.name
                    self.names[alias.asname or root] = (
                        alias.name if alias.asname else root
                    )
            elif isinstance(node, ast.ClassDef):
                self.classes[node.name] = node

    def qualify(self, name: str) -> str:
        """
        Resolve the first component of a module-local reference.

        Parameters
        ----------
        name
            Local name or dotted reference from the module.

        Returns
        -------
        str
            Qualified reference with the original attribute suffix.
        """
        first, dot, rest = name.partition(".")
        return self.names.get(first, f"{self.name}.{first}") + dot + rest


class _Annotations(ast.NodeTransformer):
    """Use qualified imports so inherited methods cannot shadow each other's types."""

    def __init__(
        self,
        module: _Module,
        imports: set[str],
        contract: str,
        aliases: dict[str, str],
    ) -> None:
        """
        Initialize the context for copying a service annotation into a facade.

        Parameters
        ----------
        module
            Source module of the service declaration.
        imports
            Import statements shared by the generated declarations.
        contract
            Qualified service class used for receiver-dependent return types.
        aliases
            Existing import aliases shared by inherited declarations.

        Returns
        -------
        None
            Prepare name resolution for the current declaration.
        """
        self.module = module
        """Module in which the original annotation was written."""
        self.imports = imports
        """Import statements accumulated for the generated stub."""
        self.contract = contract
        """Qualified service class substituted for receiver-dependent types."""
        self.parameters: set[str] = set()
        """Type parameters bound by the current method."""
        self.receiver_parameter: str | None = None
        """Type parameter that represents the service receiver, when present."""
        self.bindings: dict[str, ast.expr] = {}
        """Type arguments supplied by a specialization of the declaring class."""
        self.class_names: dict[str, str] = {}
        """Qualified references to nested classes and type aliases."""
        self.aliases = aliases
        """Generated import aliases and the qualified names they represent."""

    def bindClass(self, definition: ast.ClassDef) -> None:
        """
        Resolve nested declaration names against their declaring class.

        Parameters
        ----------
        definition
            Class whose nested types may appear in method signatures.

        Returns
        -------
        None
            Record the qualified names of its nested classes and type aliases.
        """
        for declaration in _declarations(definition.body):
            if isinstance(declaration, ast.ClassDef):
                local = declaration.name
            elif isinstance(declaration, ast.TypeAlias):
                local = declaration.name.id
            else:
                continue
            self.class_names[local] = f"{self.module.name}.{definition.name}.{local}"

    def visit(self, node: ast.AST) -> ast.AST:
        """
        Rewrite annotation references for use outside the service module.

        Parameters
        ----------
        node
            Syntax node from the original annotation.

        Returns
        -------
        ast.AST
            Transformed node with names resolved in their original context.
        """
        if isinstance(node, ast.Name):
            return self._name(node)
        if isinstance(node, ast.Attribute):
            return self._attribute(node)
        if isinstance(node, ast.Subscript):
            return self._subscript(node)
        return self.generic_visit(node)

    def _name(self, node: ast.Name) -> ast.expr:
        """
        Resolve an annotation identifier in the current type scope.

        Parameters
        ----------
        node
            Unqualified name from a service annotation.

        Returns
        -------
        ``ast.expr``
            Reference to a built-in, type parameter or importable service type.
        """
        if node.id == self.receiver_parameter:
            return ast.parse(self.contract, mode="eval").body
        if node.id in self.parameters:
            return node
        if node.id in self.bindings:
            return self.bindings[node.id]
        if node.id in self.class_names:
            self.imports.add(f"import {self.module.name}")
            return ast.parse(self.class_names[node.id], mode="eval").body
        full = self.module.qualify(node.id)
        if full in {"typing.Self", "typing_extensions.Self"}:
            full = self.contract
        elif node.id not in self.module.names and hasattr(builtins, node.id):
            return node
        module = self.module.imported_modules.get(node.id) or full.rpartition(".")[0]
        self.imports.add(f"import {module or full}")
        return ast.parse(full, mode="eval").body

    def _attribute(self, node: ast.Attribute) -> ast.expr:
        """
        Resolve a dotted attribute and register any needed submodule import.

        Parameters
        ----------
        node
            Attribute reference from a service annotation.

        Returns
        -------
        ``ast.expr``
            Expression that names the same attribute in the generated stub.
        """
        if self.module.qualify(ast.unparse(node)) in {
            "typing.Self",
            "typing_extensions.Self",
        }:
            return ast.parse(self.contract, mode="eval").body
        # A name imported from a package may be a submodule absent from its
        # __init__. Reproduce that import explicitly instead of importing only
        # the package; distinct bases can use the same local spelling.
        if isinstance(node.value, ast.Name):
            local = node.value.id
            if local in self.module.names and local not in self.module.imported_modules:
                full = self.module.names[local]
                package, _, member = full.rpartition(".")
                alias = f"_{member}"
                while self.aliases.setdefault(alias, full) != full:
                    alias += "_"
                self.imports.add(f"from {package} import {member} as {alias}")
                node.value = ast.Name(id=alias, ctx=ast.Load())
                return node
        node.value = self.annotation(node.value)
        return node

    def _subscript(self, node: ast.Subscript) -> ast.expr:
        """
        Resolve the arguments of a parameterized type.

        Parameters
        ----------
        node
            Type expression with arguments inside square brackets.

        Returns
        -------
        ``ast.expr``
            Qualified type expression preserving literal values and metadata.
        """
        # Literal values and Annotated metadata can contain ordinary strings.
        name = self.module.qualify(ast.unparse(node.value))
        node.value = self.annotation(node.value)
        if name in {"typing.Literal", "typing_extensions.Literal"}:
            node.slice = self._expression(node.slice)
        elif isinstance(node.slice, ast.Tuple):
            for i, item in enumerate(node.slice.elts):
                if i and name in {"typing.Annotated", "typing_extensions.Annotated"}:
                    node.slice.elts[i] = self._expression(item)
                else:
                    node.slice.elts[i] = self.annotation(item)
        else:
            node.slice = self.annotation(node.slice)
        return node

    def _expression(self, node: ast.expr) -> ast.expr:
        """
        Transform an expression while preserving its syntax category.

        Parameters
        ----------
        node
            Expression to visit during annotation resolution.

        Returns
        -------
        ``ast.expr``
            Transformed annotation or metadata expression.
        """
        value = self.visit(node)
        if not isinstance(value, ast.expr):
            message = "Expected an annotation expression."
            raise TypeError(message)
        return value

    @overload
    def annotation(self, value: ast.expr) -> ast.expr: ...

    @overload
    def annotation(self, value: None) -> None: ...

    def annotation(self, value: ast.expr | None) -> ast.expr | None:
        """
        Resolve a quoted forward reference or an ordinary annotation.

        Parameters
        ----------
        value
            Annotation expression, or None for an unannotated position.

        Returns
        -------
        ``ast.expr`` or None
            Resolved expression, or None if the source omitted the annotation.
        """
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            value = ast.parse(value.value, mode="eval").body
        return self._expression(value) if value is not None else None


def _bind_receiver(
    node: Method,
    annotations: _Annotations,
    decorators: set[str],
) -> tuple[ast.arg | None, ...]:
    """
    Replace the service receiver, preserving caller-supplied keyword names.

    Parameters
    ----------
    node
        Copy of the service method whose receiver will be replaced.
    annotations
        Context that tracks the receiver's type parameter.
    decorators
        Names of the decorators on the service method.

    Returns
    -------
    tuple
        Original caller-supplied parameters, including variadic positions.
    """
    args = node.args
    positional = args.posonlyargs or args.args
    original = (
        positional.pop(0) if "staticmethod" not in decorators and positional else None
    )
    receiver_type = original.annotation if original is not None else None
    if "classmethod" in decorators and isinstance(receiver_type, ast.Subscript):
        receiver_type = receiver_type.slice
    receiver_name = receiver_type.id if isinstance(receiver_type, ast.Name) else None
    annotations.receiver_parameter = None
    for parameter in node.type_params.copy():
        if isinstance(parameter, _TYPE_PARAMETERS) and parameter.name == receiver_name:
            annotations.receiver_parameter = receiver_name
            node.type_params.remove(parameter)
    arguments = (
        *args.posonlyargs,
        *args.args,
        *args.kwonlyargs,
        args.vararg,
        args.kwarg,
    )
    names = {arg.arg for arg in arguments if arg is not None}
    receiver = "cls"
    while receiver in names:
        receiver = "_" + receiver
    positional.insert(0, ast.arg(arg=receiver))
    return arguments


def _signature(method: Method, annotations: _Annotations, decorators: set[str]) -> str:
    """
    Preserve parameter kinds, overloads, defaults and coroutine behavior.

    Parameters
    ----------
    method
        Service method whose declaration is being copied.
    annotations
        Context for resolving parameter and return annotations.
    decorators
        Names of decorators on the original declaration.

    Returns
    -------
    str
        Python stub declaration for the facade member.
    """
    node = deepcopy(method)
    arguments = _bind_receiver(node, annotations, decorators)
    annotations.parameters = {
        item.name for item in node.type_params if isinstance(item, _TYPE_PARAMETERS)
    }
    for parameter in node.type_params:
        annotations.generic_visit(parameter)
    node.returns = annotations.annotation(node.returns)
    if "property" in decorators:
        annotations.imports.add("from typing import ClassVar")
        value = ast.unparse(node.returns) if node.returns else "object"
        return f"{node.name}: ClassVar[{value}]"

    for arg in arguments:
        if arg is not None:
            arg.annotation = annotations.annotation(arg.annotation)
    # Expressions used as defaults belong to the service's module and need
    # not be evaluated or copied into a typing interface.
    args = node.args
    args.defaults = [
        default if isinstance(default, ast.Constant) else ast.Constant(...)
        for default in args.defaults
    ]
    args.kw_defaults = [
        default
        if default is None or isinstance(default, ast.Constant)
        else ast.Constant(...)
        for default in args.kw_defaults
    ]
    node.decorator_list = [ast.Name(id="classmethod", ctx=ast.Load())]
    if "overload" in decorators:
        annotations.imports.add("from typing import overload")
        node.decorator_list.insert(0, ast.Name(id="overload", ctx=ast.Load()))
    node.body = [ast.Expr(ast.Constant(...))]
    rendered = ast.unparse(ast.fix_missing_locations(node))
    if isinstance(node, ast.AsyncFunctionDef) and any(
        isinstance(child, (ast.Yield, ast.YieldFrom)) for child in ast.walk(method)
    ):
        rendered = rendered.replace("\nasync def ", "\ndef ", 1)
    return rendered.replace(":\n    ...", ": ...")


def _load_module(name: str, roots: tuple[Path, ...]) -> _Module:
    """
    Find source directly, including packages whose initializers have side effects.

    Parameters
    ----------
    name
        Qualified module name to locate.
    roots
        Directories searched in order for a package, stub or source module.

    Returns
    -------
    _Module
        Parsed module with the declarations needed for signature resolution.
    """
    relative = Path(*name.split("."))
    candidates = (
        relative / "__init__.pyi",
        relative / "__init__.py",
        relative.with_suffix(".pyi"),
        relative.with_suffix(".py"),
    )
    for root in roots:
        for candidate in candidates:
            path = root / candidate
            if path.is_file():
                try:
                    return _Module(name, path)
                except SyntaxError as exc:
                    message = f"Invalid Python source for {name!r}: {exc.msg}"
                    raise ValueError(message) from exc
    message = f"No Python source found for contract module {name!r}."
    raise ValueError(message)


def _declared_methods( # NOSONAR
    module: _Module,
    definition: ast.ClassDef,
    annotations: _Annotations,
) -> Iterator[tuple[str, list[str]]]:
    """
    Select the public service methods and their overloads.

    Parameters
    ----------
    module
        Module containing the class definition.
    definition
        Class providing the members to publish on the facade.
    annotations
        Context used to render member types and imports.

    Yields
    ------
    tuple
        Public member name and the stub declarations for that member.
    """
    reserved = {"resolve", "pin", "unpin", "getFacadeAccessor"}
    own: dict[str, list[tuple[Method, set[str]]]] = {}
    for method in _declarations(definition.body):
        if isinstance(method, ast.AnnAssign) and isinstance(method.target, ast.Name):
            key = method.target.id
            if not key.startswith("_") and key not in reserved:
                value = method.annotation
                if isinstance(value, ast.Subscript) and module.qualify(
                    ast.unparse(value.value),
                ) in {"typing.ClassVar", "typing.Final"}:
                    value = value.slice
                annotations.imports.add("from typing import ClassVar")
                annotation = annotations.annotation(deepcopy(value))
                yield key, [f"{key}: ClassVar[{ast.unparse(annotation)}]"]
            continue
        if not isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if method.name.startswith("_") or method.name in reserved:
            continue
        decorators = {
            module.qualify(ast.unparse(d)).split(".")[-1] for d in method.decorator_list
        }
        if not {"setter", "deleter"}.intersection(decorators):
            own.setdefault(method.name, []).append((method, decorators))
    for key, variants in own.items():
        overloads = [item for item in variants if "overload" in item[1]]
        yield (
            key,
            [_signature(m, annotations, d) for m, d in overloads or variants[-1:]],
        )


def _parameters(definition: ast.ClassDef, module: _Module) -> list[str]:
    """
    List parameters declared with Python generics or the Generic base.

    Parameters
    ----------
    definition
        Class whose generic parameters are being inspected.
    module
        Module used to resolve imported generic base classes.

    Returns
    -------
    list[str]
        Type parameter names in declaration order.
    """
    if definition.type_params:
        return [
            p.name for p in definition.type_params if isinstance(p, _TYPE_PARAMETERS)
        ]
    for base in definition.bases:
        if not isinstance(base, ast.Subscript):
            continue
        if module.qualify(ast.unparse(base.value)) in {
            "typing.Generic",
            "typing.Protocol",
        }:
            args = (
                base.slice.elts if isinstance(base.slice, ast.Tuple) else [base.slice]
            )
            return [v.id for v in args if isinstance(v, ast.Name)]
    return []


def _bind_parameters(
    marker: type,
    definition: ast.ClassDef,
    annotations: _Annotations,
    arguments: dict[type, list[ast.expr]],
    bases: list[tuple[type, ast.expr]],
) -> None:
    """
    Propagate type arguments to methods inherited from a specialized base.

    Parameters
    ----------
    marker
        Class representing this position in the service hierarchy.
    definition
        Source declaration for the current class.
    annotations
        Context receiving the class's type substitutions.
    arguments
        Specialized type arguments indexed by hierarchy marker.
    bases
        Parent markers paired with the source expressions for those bases.

    Returns
    -------
    None
        Record substitutions for this class and its generic parents.
    """
    for index, name in enumerate(_parameters(definition, annotations.module)):
        values = arguments.get(marker, [])
        if index < len(values):
            annotations.bindings[name] = values[index]
        else:
            annotations.imports.add("import typing")
            annotations.bindings[name] = ast.parse("typing.Any", mode="eval").body
    for parent, base in bases:
        if isinstance(base, ast.Subscript) and parent not in arguments:
            args = (
                base.slice.elts if isinstance(base.slice, ast.Tuple) else [base.slice]
            )
            arguments[parent] = [annotations.annotation(deepcopy(arg)) for arg in args]


def _qualified_name(contract: str) -> str:
    """
    Validate the module and class components before locating source files.

    Parameters
    ----------
    contract
        Python class reference with a dot or colon before the class name.

    Returns
    -------
    str
        Dotted module and class name used by the source loader.
    """
    if not isinstance(contract, str):
        message = "The contract must be a qualified Python class name."
        raise TypeError(message)
    contract = contract.replace(":", ".")
    if "." not in contract or any(
        not part.isidentifier() or keyword.iskeyword(part)
        for part in contract.split(".")
    ):
        message = f"Invalid qualified contract name: {contract!r}"
        raise ValueError(message)
    return contract


def interface_replacements( # NOSONAR
    contract: str | None,
    directory: Path,
) -> dict[str, str]:
    """
    Generate typing declarations for the contract identified by module and class.

    Parameters
    ----------
    contract
        Qualified service class name, or None to generate an empty stub.
    directory
        Application root searched before the interpreter's import paths.

    Returns
    -------
    dict[str, str]
        Import and member replacements for the facade interface template.
    """
    if contract is None:
        return {"contract_imports": "", "contract_methods": "    ..."}
    contract = _qualified_name(contract)
    imports = {f"import {contract.rpartition('.')[0]}"}
    roots = (directory, *(Path(item) for item in sys.path))
    load = cache(_load_module)
    signatures: dict[str, list[str]] = {}
    aliases: dict[str, str] = {}
    ignored = {
        "abc.ABC",
        "typing.Protocol",
        "typing.Generic",
        "typing_extensions.Protocol",
    }
    definitions: dict[type, tuple[_Module, ast.ClassDef]] = {}
    arguments: dict[type, list[ast.expr]] = {}
    base_specs: dict[type, list[tuple[type, ast.expr]]] = {}

    @cache
    def hierarchy(qualified: str) -> type:
        """Use Python's MRO on empty marker types, never on application classes.

        Parameters
        ----------
        qualified
            Qualified name of the class to represent.

        Returns
        -------
        type
            Marker whose method resolution order matches the declared bases.
        """
        name, _, cls = qualified.rpartition(".")
        module = load(name, roots)
        if cls not in module.classes:
            if cls in module.names:
                return hierarchy(module.names[cls])
            message = f"No class {cls!r} in contract module {name!r}."
            raise ValueError(message)
        definition = module.classes[cls]
        bases = []
        for base in definition.bases:
            node = base.value if isinstance(base, ast.Subscript) else base
            parent = module.qualify(ast.unparse(node))
            if ast.unparse(node) != "object" and parent not in ignored:
                bases.append((hierarchy(parent), base))
        marker = type(cls, tuple(parent for parent, _ in bases), {})
        base_specs[marker] = bases
        definitions[marker] = (module, definition)
        return marker

    for marker in hierarchy(contract).__mro__[:-1]:
        module, definition = definitions[marker]
        annotations = _Annotations(module, imports, contract, aliases)
        annotations.bindClass(definition)
        _bind_parameters(marker, definition, annotations, arguments, base_specs[marker])
        for key, methods in _declared_methods(module, definition, annotations):
            signatures.setdefault(key, methods)
    methods = [
        "@classmethod\ndef getFacadeAccessor(cls) -> str: ...",
        (
            "@classmethod\nasync def resolve(cls, *args: object, **kwargs: object)"
            f" -> {contract}: ..."
        ),
        *(method for variants in signatures.values() for method in variants),
    ]
    return {
        "contract_imports": "\n" + "\n".join(sorted(imports)),
        "contract_methods": indent("\n\n".join(methods), "    "),
    }
