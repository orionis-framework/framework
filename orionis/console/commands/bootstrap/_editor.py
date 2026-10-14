from __future__ import annotations
import ast
import io
import json
import os
import tempfile
import tokenize
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

class BootstrapEditError(ValueError):
    """A bootstrap cannot be updated without guessing about application flow."""

class BootstrapEditor:
    """Plan surgical Python edits and publish them without clobbering changes.

    The editor deliberately does not execute user code. Unsupported or ambiguous
    construction flows fail before any file is changed.
    """

    # ruff: noqa:C901

    def __init__(self, path: Path, base_path: Path) -> None:
        """
        Initialize a source-preserving application bootstrap edit session.

        Parameters
        ----------
        path : Path
            Bootstrap Python module to inspect.
        base_path : Path
            Application root used for relative route and import paths.

        Returns
        -------
        None
            Store the original source, syntax tree, and application binding.
        """
        # Capture source metadata before planning any modifications.
        self.path = Path(path)
        self.base_path = Path(base_path).resolve()
        self._original = self.path.read_bytes()
        self.encoding, _ = tokenize.detect_encoding(io.BytesIO(self._original).readline)
        self.source = self._original.decode(self.encoding)
        self.newline = "\r\n" if "\r\n" in self.source else "\n"
        try:
            self.tree = ast.parse(self.source, filename=str(self.path))
        except SyntaxError as exc:
            error_msg = f"Invalid Python in {self.path}: {exc}"
            raise BootstrapEditError(error_msg) from exc
        self._lines = self.source.splitlines(keepends=True)
        self._offsets = [0]
        for line in self._lines:
            self._offsets.append(self._offsets[-1] + len(line))
        self._parents = {
            child: parent
            for parent in ast.walk(self.tree)
            for child in ast.iter_child_nodes(parent)
        }
        self.assignment, self.app_name = self._find_application()
        self.scope = self._parents[self.assignment]
        if not isinstance(
            self.scope, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            error_msg = (
                f"Conditional Application construction in {self.path} "
                "cannot be edited safely."
            )
            raise BootstrapEditError(error_msg)
        self.body = self.scope.body
        self._nodes = list(self._scope_nodes(self.scope))
        self._check_assignments()

    def _application_names(self) -> tuple[set[str], set[str]]:
        """
        Collect supported application constructor and module aliases.

        Returns
        -------
        tuple[set[str], set[str]]
            Return constructor names and imported application module names.
        """
        # Resolve only imports recognized by the application builder.
        constructors = {"Application"}
        modules = set()
        for node in self.tree.body:
            if isinstance(node, ast.ImportFrom) and node.module in {
                "orionis",
                "orionis.foundation.application",
            }:
                constructors.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "Application"
                )
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in {"orionis", "orionis.foundation.application"}:
                        modules.add(alias.asname or alias.name)

        return constructors, modules

    @staticmethod
    def _is_constructor(
        node: ast.AST, constructors: set[str], modules: set[str],
    ) -> bool:
        """
        Identify an application constructor beneath chained builder calls.

        Parameters
        ----------
        node : ast.AST
            Expression to inspect.
        constructors : set[str]
            Recognized direct application constructor names.
        modules : set[str]
            Recognized imported application module names.

        Returns
        -------
        bool
            Return whether the expression constructs the application.
        """
        # Follow fluent calls back to their original constructor.
        while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "Application":
                break
            node = node.func.value
        if not isinstance(node, ast.Call):
            return False
        if isinstance(node.func, ast.Name):
            return node.func.id in constructors
        if isinstance(node.func, ast.Attribute) and node.func.attr == "Application":
            return ast.unparse(node.func.value) in modules
        return False

    def _find_application(self) -> tuple[ast.Assign | ast.AnnAssign, str]:
        """
        Locate the unique named application construction assignment.

        Returns
        -------
        tuple[ast.Assign | ast.AnnAssign, str]
            Return the assignment node and its application variable name.
        """
        # Require one unambiguous named application construction.
        constructors, modules = self._application_names()
        candidates = []
        for node in ast.walk(self.tree):
            target = None
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
            elif isinstance(node, ast.AnnAssign):
                target = node.target
            if (
                isinstance(target, ast.Name)
                and node.value is not None
                and self._is_constructor(node.value, constructors, modules)
            ):
                candidates.append((node, target.id))
        if len(candidates) != 1:
            error_msg = f"Cannot identify one Application assignment in {self.path}."
            raise BootstrapEditError(error_msg)
        return candidates[0]

    def _check_assignments(self) -> None:
        """
        Reject application reassignments that obscure the selected receiver.

        Returns
        -------
        None
            Complete validation without changing the application source.
        """
        # Check bindings throughout the selected lexical scope.
        for node in self._nodes:
            if node is self.assignment:
                continue
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                targets = [node.target]
            if any(
                isinstance(t, ast.Name) and t.id == self.app_name for t in targets
            ) and (
                not isinstance(node, ast.Assign)
                or self._root_name(node.value) != self.app_name
            ):
                error_msg = (
                    f"Application {self.app_name!r} is reassigned in {self.path}."
                )
                raise BootstrapEditError(error_msg)

    @staticmethod
    def _scope_nodes(scope: ast.AST) -> Iterator[ast.AST]:
        """
        Walk a lexical scope without entering unrelated nested definitions.

        Parameters
        ----------
        scope : ast.AST
            Lexical scope or descendant node to traverse.

        Yields
        ------
        ast.AST
            Emit nodes from the selected lexical scope.

        Returns
        -------
        None
            Finish traversal without returning a value.
        """
        # Keep nested lexical scopes outside the application inspection.
        yield scope
        for child in ast.iter_child_nodes(scope):
            if isinstance(
                child,
                (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda),
            ):
                continue
            yield from BootstrapEditor._scope_nodes(child)

    @staticmethod
    def _root_name(node: ast.AST | None) -> str | None:
        """
        Resolve the named receiver beneath a fluent method-call chain.

        Parameters
        ----------
        node : ast.AST | None
            Expression to inspect, or None when no expression exists.

        Returns
        -------
        str | None
            Return the receiver name, or None for an unnamed expression.
        """
        # Unwrap chained calls without evaluating application code.
        while isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            node = node.func.value
        return node.id if isinstance(node, ast.Name) else None

    def _position(self, lineno: int, byte_column: int) -> int:
        # AST columns are UTF-8 byte offsets, even for non-UTF-8 source files.
        """
        Translate an AST byte position into a source character offset.

        Parameters
        ----------
        lineno : int
            One-based source line number.
        byte_column : int
            Zero-based UTF-8 byte column from the AST.

        Returns
        -------
        int
            Return the absolute character offset in the original source.
        """
        # AST columns use UTF-8 bytes regardless of the source encoding.
        line = self._lines[lineno - 1]
        prefix = line.encode("utf-8")[:byte_column].decode("utf-8")
        return self._offsets[lineno - 1] + len(prefix)

    def _start(self, node: ast.AST) -> int:
        """
        Locate the first source character belonging to a syntax node.

        Parameters
        ----------
        node : ast.AST
            Syntax node with source location information.

        Returns
        -------
        int
            Return the absolute start offset in the original source.
        """
        # Translate the node start through the original line offsets.
        return self._position(node.lineno, node.col_offset)

    def _end(self, node: ast.AST) -> int:
        """
        Locate the source character immediately after a syntax node.

        Parameters
        ----------
        node : ast.AST
            Syntax node with complete source location information.

        Returns
        -------
        int
            Return the exclusive end offset in the original source.
        """
        # Translate the node end through the original line offsets.
        return self._position(node.end_lineno, node.end_col_offset)

    def _statement(self, node: ast.AST) -> ast.stmt:
        """
        Find the enclosing statement in the application construction scope.

        Parameters
        ----------
        node : ast.AST
            Descendant syntax node whose enclosing statement is needed.

        Returns
        -------
        ast.stmt
            Return the statement that belongs directly to the selected scope.
        """
        # Ascend to the statement that can safely receive an insertion.
        while self._parents.get(node) is not self.scope:
            node = self._parents[node]
        if node not in self.body:
            error_msg = f"Cannot locate a safe insertion point in {self.path}."
            raise BootstrapEditError(error_msg)
        return node

    def _calls(self, method: str) -> list[ast.Call]:
        """
        Collect editable calls to an application builder method.

        Parameters
        ----------
        method : str
            Application method name to locate.

        Returns
        -------
        list[ast.Call]
            Return matching calls ordered by their source end offsets.
        """
        # Inspect both named receivers and calls inside the initializer.
        calls = []
        initializer_nodes = self._initializer_calls()
        for node in self._nodes:
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == method
            ):
                continue
            if self._root_name(node) == self.app_name or node in initializer_nodes:
                statement = self._statement(node)
                if not isinstance(
                    statement, (ast.Expr, ast.Assign, ast.AnnAssign, ast.Return),
                ):
                    error_msg = (
                        f"Conditional {method}() in {self.path} "
                        "cannot be edited safely."
                    )
                    raise BootstrapEditError(
                        error_msg,
                    )
                calls.append(node)
        return sorted(calls, key=self._end)

    def _initializer_calls(self) -> set[ast.Call]:
        """
        Collect fluent calls that construct the named application.

        Returns
        -------
        set[ast.Call]
            Return the calls in the application assignment value chain.
        """
        # Follow the initializer receiver chain without visiting arguments.
        calls = set()
        node = self.assignment.value
        while isinstance(node, ast.Call):
            calls.add(node)
            if not isinstance(node.func, ast.Attribute):
                break
            node = node.func.value
        return calls

    def _routing_call(self) -> ast.Call | None:
        """
        Find the final directly editable application routing call.

        Returns
        -------
        ast.Call | None
            Return the effective routing call, or None when it is absent.
        """
        # Use the last routing call because it replaces earlier configuration.
        calls = self._calls("withRouting")
        return calls[-1] if calls else None

    @property
    def hasRouting(self) -> bool:
        """
        Report whether the application exposes a directly editable routing call.

        Returns
        -------
        bool
            Return whether a supported routing call exists.
        """
        # Inspect the selected application routing configuration.
        return self._routing_call() is not None

    @staticmethod
    def _routing_value(call: ast.Call, context: str) -> ast.AST | None:
        """
        Find a context argument in a supported routing call.

        Parameters
        ----------
        call : ast.Call
            Routing call to inspect.
        context : str
            Runtime context whose route argument is needed.

        Returns
        -------
        ast.AST | None
            Return the argument expression, or None when it is absent.
        """
        # Respect the public positional order before inspecting keywords.
        positionals = ("api", "web", "console", "health", "ai")
        if any(isinstance(value, ast.Starred) for value in call.args):
            error_msg = "Cannot safely inspect withRouting(*args)."
            raise BootstrapEditError(error_msg)
        if context in positionals and len(call.args) > positionals.index(context):
            return call.args[positionals.index(context)]
        return next(
            (keyword.value for keyword in call.keywords if keyword.arg == context),
            None,
        )

    def routePaths(self, context: str) -> list[str] | None:
        """
        Read literal route paths from the effective routing configuration.

        Parameters
        ----------
        context : str
            Runtime context whose configured paths are needed.

        Returns
        -------
        list[str] | None
            Return literal paths, an empty list if unset, or None if dynamic.
        """
        # Distinguish omitted contexts from unresolved expanded arguments.
        call = self._routing_call()
        if call is None:
            return []
        value = self._routing_value(call, context)
        if value is None or (isinstance(value, ast.Constant) and value.value is None):
            expanded = value is None and any(kw.arg is None for kw in call.keywords)
            return None if expanded else []
        try:
            literal = ast.literal_eval(value)
        except ValueError, TypeError:
            return None
        if isinstance(literal, str):
            return [literal] if literal else []
        if isinstance(literal, (list, tuple)) and all(
            isinstance(v, str) for v in literal
        ):
            return list(literal)
        return None

    def _path_literal(self, path: Path) -> str:
        """
        Encode a route path as a project-relative Python string literal.

        Parameters
        ----------
        path : Path
            Effective route file path to represent.

        Returns
        -------
        str
            Return a quoted relative path, or an absolute path outside the root.
        """
        # Prefer portable project-relative paths whenever possible.
        resolved = Path(path).resolve()
        try:
            path_text = resolved.relative_to(self.base_path).as_posix()
        except ValueError:
            path_text = resolved.as_posix()
        # ASCII escapes preserve paths under any supported source encoding.
        return json.dumps(path_text)

    def _edited(self, edits: list[tuple[int, int, str]]) -> str:
        """
        Apply planned source edits and validate the resulting Python module.

        Parameters
        ----------
        edits : list[tuple[int, int, str]]
            Start offsets, exclusive end offsets, and replacement text.

        Returns
        -------
        str
            Return syntactically valid source in the original encoding.
        """
        # Apply replacements backwards so original offsets remain valid.
        result = self.source
        for start, end, content in sorted(edits, reverse=True):
            result = result[:start] + content + result[end:]
        try:
            compile(result, str(self.path), "exec")
        except SyntaxError as exc:
            error_msg = f"Cannot safely preserve Python syntax in {self.path}: {exc}"
            raise BootstrapEditError(error_msg) from exc
        # Check the original encoding before any file or directory is changed.
        result.encode(self.encoding)
        return result

    def _before(self, statement: ast.stmt, lines: list[str]) -> tuple[int, int, str]:
        """
        Plan an insertion before a statement and its leading comments.

        Parameters
        ----------
        statement : ast.stmt
            Standalone statement that follows the inserted lines.
        lines : list[str]
            Unindented source lines to insert.

        Returns
        -------
        tuple[int, int, str]
            Return the insertion offsets and correctly indented source text.
        """
        # Preserve comments attached to the existing statement.
        start = self._offsets[statement.lineno - 1]
        indent = self._lines[statement.lineno - 1][: statement.col_offset]
        if indent.strip():
            error_msg = f"Inline statements in {self.path} cannot be edited safely."
            raise BootstrapEditError(error_msg)
        # Keep any leading comment attached to the existing statement.
        while start and statement.lineno > 1:
            previous_line = self.source[:start].splitlines(keepends=True)[-1]
            if (
                not previous_line.lstrip().startswith("#")
                or previous_line[: len(indent)] != indent
            ):
                break
            start -= len(previous_line)
        content = "".join(indent + line + self.newline for line in lines)
        return start, start, content + self.newline

    def _after(
        self, statement: ast.stmt, lines: list[str], *, separate: bool = True,
    ) -> tuple[int, int, str]:
        """
        Plan an insertion after a standalone statement.

        Parameters
        ----------
        statement : ast.stmt
            Standalone statement that precedes the inserted lines.
        lines : list[str]
            Unindented source lines to insert.
        separate : bool
            Whether to separate the insertion with a leading blank line.

        Returns
        -------
        tuple[int, int, str]
            Return the insertion offsets and correctly indented source text.
        """
        # Reject inline statements whose boundaries cannot be preserved.
        end = self._offsets[statement.end_lineno]
        suffix = self._lines[statement.end_lineno - 1][
            len(
                self._lines[statement.end_lineno - 1]
                .encode("utf-8")[: statement.end_col_offset]
                .decode("utf-8"),
            ) :
        ].strip()
        if suffix and not suffix.startswith("#"):
            error_msg = f"Semicolon statements in {self.path} cannot be edited safely."
            raise BootstrapEditError(error_msg)
        indent = self._lines[statement.lineno - 1][: statement.col_offset]
        if indent.strip():
            error_msg = f"Inline statements in {self.path} cannot be edited safely."
            raise BootstrapEditError(error_msg)
        prefix = self.newline if end and self.source[end - 1] not in "\r\n" else ""
        content = (
            prefix
            + (self.newline if separate else "")
            + "".join(indent + line + self.newline for line in lines)
        )
        return end, end, content

    def _callback_import(self, import_line: str) -> tuple[int, int, str]:
        """
        Extend the visible import block without adding an empty import group.

        Parameters
        ----------
        import_line : str
            Callback import to insert in the application construction scope.

        Returns
        -------
        tuple[int, int, str]
            Return insertion offsets and source with existing spacing preserved.
        """
        # Append within the same scope while retaining existing import groups.
        imports = [
            node for node in self.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
            and node.end_lineno < self.assignment.lineno
        ]
        if imports:
            last = imports[-1]
            future_only = (
                isinstance(last, ast.ImportFrom) and last.module == "__future__"
            )
            return self._after(last, [import_line], separate=future_only)
        start, end, content = self._before(self.assignment, [import_line])
        if isinstance(self.scope, ast.Module) and self.body[0] is self.assignment:
            # Keep shebangs, coding cookies, and module headers at the top.
            start = end = self._offsets[self.assignment.lineno - 1]
        return start, end, content

    def _registration(self, lines: list[str]) -> list[tuple[int, int, str]]: # NOSONAR
        """
        Plan registration before application initialization or factory return.

        Parameters
        ----------
        lines : list[str]
            Unindented registration source lines to insert.

        Returns
        -------
        list[tuple[int, int, str]]
            Return source edits that preserve the initialization order.
        """
        # Select an insertion point before initialization can consume settings.
        if isinstance(self.scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
            returns = [node for node in self._nodes if isinstance(node, ast.Return)]
            if len(returns) > 1 or any(
                self._statement(node) is not node for node in returns
            ):
                error_msg = (
                    f"Conditional application returns in {self.path} are ambiguous."
                )
                raise BootstrapEditError(error_msg)
        creates = self._calls("create") + self._calls("boot")
        creates.sort(key=self._start)
        if creates:
            create = creates[0]
            statement = self._statement(create)
            if statement is self.assignment:
                # A terminal chained create is split only after the builder has
                # produced the named application instance.
                if create is not self.assignment.value and not (
                    isinstance(self.assignment.value, ast.Call)
                    and self.assignment.value is create
                ):
                    error_msg = (
                        f"Non-terminal create() chain in {self.path} is ambiguous."
                    )
                    raise BootstrapEditError(error_msg)
                if create.args or create.keywords:
                    error_msg = (
                        f"Cannot safely move create()/boot() arguments in {self.path}."
                    )
                    raise BootstrapEditError(error_msg)
                suffix_start = self._end(create.func.value)
                suffix_end = self._end(create)
                return [
                    (suffix_start, suffix_end, ""),
                    self._after(
                        statement, [*lines, f"{self.app_name}.{create.func.attr}()"],
                    ),
                ]
            return [self._before(statement, lines)]
        returns = [node for node in self.body if isinstance(node, ast.Return)]
        if returns:
            if len(returns) != 1 or self._root_name(returns[0].value) != self.app_name:
                error_msg = f"Cannot identify the application return in {self.path}."
                raise BootstrapEditError(error_msg)
            return [self._before(returns[0], lines)]
        return [self._after(self.assignment, lines)]

    def routing(
        self, context: str, route_path: Path | list[Path], *, registered: bool = False,
    ) -> str | None:
        """
        Register a missing route context while preserving other arguments.

        Parameters
        ----------
        context : str
            Runtime context to register.
        route_path : Path | list[Path]
            Effective route file path or paths to register.
        registered : bool
            Whether runtime paths confirm a dynamic registration.

        Returns
        -------
        str | None
            Return updated source, or None when the context is already enabled.
        """
        # Validate source-level safety before planning the context change.
        call = self._routing_call()
        self._check_indirect_routing(call)
        literal = (
            "[" + ", ".join(self._path_literal(path) for path in route_path) + "]"
            if isinstance(route_path, list)
            else self._path_literal(route_path)
        )
        if call is None:
            creates = self._calls("create") + self._calls("boot")
            initializer = self._initializer_calls()
            if creates and creates[0] in initializer:
                create = creates[0]
                position = self._end(create.func.value)
                return self._edited(
                    [(position, position, f".withRouting({context}={literal})")],
                )
            return self._edited(
                self._registration(
                    [f"{self.app_name}.withRouting({context}={literal})"],
                ),
            )
        value = self._routing_value(call, context)
        if value is not None:
            if not (
                isinstance(value, ast.Constant) and value.value in (None, "")
            ) and not (isinstance(value, (ast.List, ast.Tuple)) and not value.elts):
                return None
            self._check_routing_order(call)
            return self._edited([(self._start(value), self._end(value), literal)])
        if any(keyword.arg is None for keyword in call.keywords):
            if registered:
                return None
            error_msg = (
                f"Cannot safely add {context!r} to withRouting(**kwargs) "
                f"in {self.path}."
            )
            raise BootstrapEditError(error_msg)
        self._check_routing_order(call)
        return self._append_keyword(call, context, literal)

    def _check_indirect_routing(self, routing: ast.Call | None) -> None:
        """
        Reject later helpers that can replace the selected routing setup.

        Parameters
        ----------
        routing : ast.Call | None
            Selected routing call, or None when registration is absent.

        Returns
        -------
        None
            Complete validation without changing the application source.
        """
        # Check later helper invocations that can overwrite direct routing.
        helpers = {
            node.name: node for node in [*self.tree.body, *self.body]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }
        boundary = self._end(routing or self.assignment)
        for node in self._nodes:
            if not (
                isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id in helpers and self._end(node) > boundary
            ):
                continue
            helper = helpers[node.func.id]
            if isinstance(helper, ast.AsyncFunctionDef) and not isinstance(
                self._parents.get(node), ast.Await,
            ):
                continue
            parameters = self._helper_application_parameters(helper, node)
            if self._helper_replaces_routing(helper, parameters):
                error_msg = (
                    f"Helper {helper.name}() can replace withRouting() after "
                    f"the selected configuration in {self.path}; "
                    "register this context in the helper explicitly."
                )
                raise BootstrapEditError(error_msg)

    def _helper_application_parameters(
        self, helper: ast.FunctionDef | ast.AsyncFunctionDef, call: ast.Call,
    ) -> set[str]:
        """
        Identify helper names that can reference the selected application.

        Parameters
        ----------
        helper : ast.FunctionDef | ast.AsyncFunctionDef
            Helper definition whose argument bindings are inspected.
        call : ast.Call
            Invocation that can pass the selected application.

        Returns
        -------
        set[str]
            Return parameter and closure names that can reference the application.
        """
        # Bind positional and keyword arguments without executing the helper.
        positional = [*helper.args.posonlyargs, *helper.args.args]
        parameters = set()
        for parameter, value in zip(positional, call.args, strict=False):
            if isinstance(value, ast.Starred):
                break
            if self._root_name(value) == self.app_name:
                parameters.add(parameter.arg)
        named = {arg.arg for arg in [*helper.args.args, *helper.args.kwonlyargs]}
        parameters.update(
            keyword.arg for keyword in call.keywords
            if keyword.arg in named and self._root_name(keyword.value) == self.app_name
        )
        # A local helper can also close over the application without receiving
        # an explicit argument. Module helpers cannot capture a factory local.
        arguments = {arg.arg for arg in [*positional, *helper.args.kwonlyargs]}
        local_bindings = {
            node.id for node in self._scope_nodes(helper)
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store)
        }
        if (
            self.app_name not in arguments | local_bindings
            and self._parents[helper] is self.scope
        ):
            parameters.add(self.app_name)
        return parameters

    def _helper_replaces_routing(
        self, helper: ast.FunctionDef | ast.AsyncFunctionDef, parameters: set[str],
    ) -> bool:
        # A supplied parameter can still reference the original application
        # after an alias assignment or a conditional rebind. Treat its routing
        # mutations as unsafe instead of assuming that rebinding isolates it.
        """
        Detect routing mutations through helper parameters or closures.

        Parameters
        ----------
        helper : ast.FunctionDef | ast.AsyncFunctionDef
            Helper definition to inspect within its lexical scope.
        parameters : set[str]
            Names that can still reference the application instance.

        Returns
        -------
        bool
            Return whether the helper can replace application routing.
        """
        # Retain aliases that may reference the application after rebinding.
        return any(
            isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
            and node.func.attr == "withRouting"
            and self._root_name(node) in parameters
            for node in self._scope_nodes(helper)
        )

    def _append_keyword( # NOSONAR
        self,
        call: ast.Call,
        context: str,
        literal: str,
    ) -> str:
        """
        Extend a routing argument list while retaining its source layout.

        Parameters
        ----------
        call : ast.Call
            Routing call whose argument list must be extended.
        context : str
            Runtime context to add as a keyword argument.
        literal : str
            Validated Python literal representing the route paths.

        Returns
        -------
        str
            Return updated source with the additional routing keyword.
        """
        # Preserve multiline indentation and trailing-comma conventions.
        end = self._end(call) - 1
        closing_line = self._lines[call.end_lineno - 1]
        closing_column = len(
            closing_line.encode("utf-8")[: call.end_col_offset - 1].decode("utf-8"),
        )
        if call.lineno != call.end_lineno and not closing_line[:closing_column].strip():
            arguments = [*call.args, *call.keywords]
            edits = []
            if arguments:
                last = max(arguments, key=self._end)
                argument_end, has_comma = self._argument_tail(last, end)
                if not has_comma:
                    edits.append((argument_end, argument_end, ","))
                indent = self._lines[arguments[0].lineno - 1][: arguments[0].col_offset]
                if indent.strip():
                    indent = closing_line[:closing_column] + "    "
            else:
                indent = closing_line[:closing_column] + "    "
            position = self._offsets[call.end_lineno - 1]
            edits.append(
                (position, position, f"{indent}{context}={literal},{self.newline}"),
            )
            return self._edited(edits)
        # Token inspection handles inline comments and existing trailing commas.
        arguments = [*call.args, *call.keywords]
        if arguments:
            last = max(arguments, key=self._end)
            tail = self.source[self._end(last) : end]
            if "#" in tail or "\n" in tail or "\r" in tail:
                error_msg = (
                    f"Cannot safely extend the inline routing call in {self.path}."
                )
                raise BootstrapEditError(error_msg)
            separator = " " if tail.rstrip().endswith(",") else ", "
        else:
            separator = ""
        return self._edited([(end, end, f"{separator}{context}={literal}")])

    def _argument_tail(self, last: ast.AST, call_end: int) -> tuple[int, bool]:
        """
        Find grouping parentheses beyond a positional argument AST node.

        Parameters
        ----------
        last : ast.AST
            Final argument node in the routing call.
        call_end : int
            Character offset immediately before the closing parenthesis.

        Returns
        -------
        tuple[int, bool]
            Return the complete argument end offset and trailing-comma presence.
        """
        # Inspect tokens because AST spans omit redundant grouping parentheses.
        start = self._end(last)
        if start > call_end:
            error_msg = f"Cannot extend an unparenthesized generator in {self.path}."
            raise BootstrapEditError(error_msg)
        tail = self.source[start:call_end]
        tail_lines = tail.splitlines(keepends=True)
        end = start
        tokens = tokenize.generate_tokens(io.StringIO(tail).readline)
        try:
            for token in tokens:
                if token.type != tokenize.OP:
                    continue
                if token.string == ",":
                    return end, True
                if token.string not in {")", "]", "}"}:
                    error_msg = (
                        f"Cannot locate the routing argument boundary in {self.path}."
                    )
                    raise BootstrapEditError(error_msg)
                line_offset = sum(map(len, tail_lines[:token.end[0] - 1]))
                end = start + line_offset + token.end[1]
        except tokenize.TokenError:
            # The suffix can contain closing parentheses whose opening tokens
            # are outside this fragment. All operators were checked above.
            return end, False
        return end, False

    def _check_routing_order(self, call: ast.Call) -> None:
        """
        Reject routing configuration placed after application initialization.

        Parameters
        ----------
        call : ast.Call
            Routing call whose initialization order must be validated.

        Returns
        -------
        None
            Complete validation without changing the application source.
        """
        # Require routing to be configured before create or boot consumes it.
        for create in self._calls("create") + self._calls("boot"):
            if self._end(create) < self._end(call):
                error_msg = (
                    f"withRouting() after create()/boot() in {self.path} "
                    "cannot be updated safely."
                )
                raise BootstrapEditError(
                    error_msg,
                )

    def lifespan(self, lifespan_path: Path) -> str | None:
        """
        Import and register application callbacks before initialization.

        Parameters
        ----------
        lifespan_path : Path
            Effective Python module containing lifespan callbacks.

        Returns
        -------
        str | None
            Return updated source, or None when callbacks are already registered.
        """
        # Resolve an importable callback module within the application root.
        resolved = Path(lifespan_path).resolve()
        try:
            relative = resolved.relative_to(self.base_path).with_suffix("")
        except ValueError as exc:
            error_msg = (
                f"Lifespan module {resolved} is outside the application import root."
            )
            raise BootstrapEditError(error_msg) from exc
        if not all(part.isidentifier() for part in relative.parts):
            error_msg = f"Lifespan module {relative} is not a valid Python module path."
            raise BootstrapEditError(error_msg)
        module = ".".join(relative.parts)
        names, modules, custom_names = self._lifespan_bindings(module)
        if self._has_lifespan_registration(names, modules, custom_names):
            return None
        if names:
            call_name = min(names)
        elif modules:
            call_name = min(modules) + ".register_lifespan_callbacks"
        else:
            call_name = self._fresh_callback_name()
        edits = self._registration(
            [
                "# Register callbacks for a specific application lifespan event.",
                f"{call_name}({self.app_name})",
            ],
        )
        if not names and not modules:
            alias = (
                "" if call_name == "register_lifespan_callbacks" else f" as {call_name}"
            )
            import_line = f"from {module} import register_lifespan_callbacks{alias}"
            edits.append(self._callback_import(import_line))
        return self._edited(edits)

    def _lifespan_bindings(  # NOSONAR
        self, module: str,
    ) -> tuple[set[str], set[str], set[str]]:
        """
        Recognize visible direct and module imports for lifespan callbacks.

        Parameters
        ----------
        module : str
            Dotted module path that supplies the generated callbacks.

        Returns
        -------
        tuple[set[str], set[str], set[str]]
            Return direct names, module names, and custom callback names.
        """
        # Inspect bindings available before the application initializes.
        names = set()
        modules = set()
        visible_nodes = [*self.tree.body, *self.body]
        custom_names = {
            node.name
            for node in visible_nodes
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "register_lifespan_callbacks"
        }
        boundaries = self._calls("create") + self._calls("boot")
        boundaries.extend(node for node in self.body if isinstance(node, ast.Return))
        cutoff = min(
            (node.lineno for node in boundaries),
            default=self.assignment.end_lineno + 1,
        )
        for node in visible_nodes:
            if node in self.body and node.lineno >= cutoff:
                continue
            if isinstance(node, ast.ImportFrom):
                imported_module = self._import_module(node)
                for alias in node.names:
                    if alias.name == "register_lifespan_callbacks":
                        if imported_module == module:
                            names.add(alias.asname or alias.name)
                        else:
                            custom_names.add(alias.asname or alias.name)
                    elif (
                        imported_module and f"{imported_module}.{alias.name}" == module
                    ):
                        modules.add(alias.asname or alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == module:
                        modules.add(alias.asname or alias.name)
        return names, modules, custom_names

    def _has_lifespan_registration(
        self,
        names: set[str],
        modules: set[str],
        custom_names: set[str],
    ) -> bool:
        """
        Detect existing callback registration for the selected application.

        Parameters
        ----------
        names : set[str]
            Directly imported names for the requested callback function.
        modules : set[str]
            Imported modules that expose the callback function.
        custom_names : set[str]
            Custom callback names whose registrations are preserved.

        Returns
        -------
        bool
            Return whether an unambiguous callback registration already exists.
        """
        # Match the callback receiver and its positional or keyword app argument.
        for node in self._nodes:
            if not isinstance(node, ast.Call):
                continue
            callback = (
                isinstance(node.func, ast.Name) and node.func.id in names | custom_names
            )
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "register_lifespan_callbacks"
            ):
                callback = ast.unparse(node.func.value) in modules
            argument = node.args[0] if node.args else next(
                (keyword.value for keyword in node.keywords if keyword.arg == "app"),
                None,
            )
            if callback and self._root_name(argument) == self.app_name:
                statement = self._statement(node)
                if not isinstance(statement, ast.Expr):
                    error_msg = (
                        f"Conditional lifespan registration in {self.path} "
                        "is ambiguous."
                    )
                    raise BootstrapEditError(error_msg)
                return True
        return False

    def _fresh_callback_name(self) -> str:
        """
        Choose an unused callback import name in the application scope.

        Returns
        -------
        str
            Return the standard callback name or a collision-free generated alias.
        """
        # Reserve identifiers introduced by assignments, definitions, and imports.
        bound_names = {
            node.id for node in ast.walk(self.scope) if isinstance(node, ast.Name)
        }
        bound_names.update(
            node.name
            for node in ast.walk(self.scope)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        )
        bound_names.update(
            alias.asname or alias.name
            for node in [*self.tree.body, *self._nodes]
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        )
        if "register_lifespan_callbacks" not in bound_names:
            return "register_lifespan_callbacks"
        suffix = 1
        while f"_orionis_lifespan_{suffix}" in bound_names:
            suffix += 1
        return f"_orionis_lifespan_{suffix}"

    def _import_module(self, node: ast.ImportFrom) -> str | None:
        """
        Resolve an import node to its absolute application module path.

        Parameters
        ----------
        node : ast.ImportFrom
            Import-from node whose module path must be resolved.

        Returns
        -------
        str | None
            Return the dotted module path, or None for an invalid relative import.
        """
        # Resolve relative imports against the bootstrap module package.
        if not node.level:
            return node.module
        try:
            package = list(self.path.parent.resolve().relative_to(self.base_path).parts)
        except ValueError:
            return None
        if node.level > len(package):
            return None
        package = package[: len(package) - node.level + 1]
        if node.module:
            package.extend(node.module.split("."))
        return ".".join(package)

    def encode(self, source: str) -> bytes:
        """
        Encode planned source using the original coding cookie and BOM.

        Parameters
        ----------
        source : str
            Validated Python source to encode.

        Returns
        -------
        bytes
            Return source bytes in the original bootstrap encoding.
        """
        # Reuse the encoding detected from the original source bytes.
        return source.encode(self.encoding)

    def commit(self, source: str | None) -> bool:
        """
        Publish validated source atomically while preserving concurrent edits.

        Parameters
        ----------
        source : str | None
            Planned source, or None when no update is required.

        Returns
        -------
        bool
            Return whether updated source was written to the bootstrap module.
        """
        # Skip identical plans and check for concurrent changes before replacing.
        if source is None or source == self.source:
            return False
        compile(source, str(self.path), "exec")
        content = self.encode(source)
        if self.path.read_bytes() != self._original:
            error_msg = (
                f"{self.path} changed during bootstrap; refusing to overwrite it."
            )
            raise BootstrapEditError(error_msg)
        mode = self.path.stat().st_mode
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=self.path.parent, prefix=".bootstrap-", delete=False,
            ) as handle:
                temporary = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.chmod(mode)
            if self.path.read_bytes() != self._original:
                error_msg = (
                    f"{self.path} changed during bootstrap; refusing to overwrite it."
                )
                raise BootstrapEditError(error_msg)
            temporary.replace(self.path)
            return True
        finally:
            if temporary is not None and temporary.exists():
                temporary.unlink()
