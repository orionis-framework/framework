from __future__ import annotations
import ast
import codecs
import io
import tokenize
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from orionis.console.commands.bootstrap._editor import (
    BootstrapEditError,
    BootstrapEditor,
)

class TestBootstrapEditor(TestCase):
    def setUp(self) -> None:
        """
        Create an isolated application bootstrap with a canonical root.

        Returns
        -------
        None
            Store temporary application paths and register cleanup.
        """
        # Isolate each test from project files and other test runs.
        self.directory = TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.base = Path(self.directory.name).resolve()
        self.path = self.base / "bootstrap" / "app.py"
        self.path.parent.mkdir()

    def editor(self, source: str) -> BootstrapEditor:
        """
        Create an editor for the supplied bootstrap source.

        Parameters
        ----------
        source : str
            Python bootstrap source to write to the fixture.

        Returns
        -------
        BootstrapEditor
            Return an editor bound to the temporary application.
        """
        # Write the fixture before loading its original source.
        self.path.write_bytes(source.encode("utf-8"))
        return BootstrapEditor(self.path, self.base)

    def assertValid(self, source: str) -> None:
        """
        Compile generated source to validate Python syntax.

        Parameters
        ----------
        source : str
            Generated Python source to compile.

        Returns
        -------
        None
            Complete compilation without returning a value.
        """
        # Validate syntax without executing the generated module.
        compile(source, str(self.path), "exec")

    def test_adds_each_routing_context_and_preserves_existing_arguments(self) -> None:
        """
        Add each route context while retaining existing arguments.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        for context in ("api", "ai", "console", "web", "websocket"):
            with self.subTest(context=context):
                source = (
                    "from orionis import Application\n"
                    "app = Application()\n"
                    "# Keep health and this comment.\n"
                    "app.withRouting(\n"
                    "    health='/up',  # Keep this endpoint.\n"
                    ")\n"
                    "app.create()\n"
                )
                editor = self.editor(source)
                result = editor.routing(context, self.base / "custom" / f"{context}.py")
                self.assertValid(result)
                self.assertIn("health='/up',  # Keep this endpoint.\n", result)
                editor.commit(result)
                unchanged = BootstrapEditor(self.path, self.base)
                self.assertIsNone(unchanged.routing(context, self.base / "ignored.py"))
                self.assertEqual(
                    unchanged.routePaths(context),
                    [f"custom/{context}.py"],
                )

    def test_adds_missing_comma_without_losing_comment(self) -> None:
        """
        Add a missing argument comma while preserving its comment.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "app = Application()\napp.withRouting(\n    health='/up'  # health\n)\n",
        )
        result = editor.routing("api", self.base / "routes/api.py")
        self.assertIn("health='/up',  # health", result)
        self.assertValid(result)

    def test_grouped_final_arguments_keep_their_original_type(self) -> None:
        """
        Place new commas outside grouping parentheses and preserve values.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        for argument, context in (
            ('health=("/up")', "api"),
            ('(("custom/api.py"))', "ai"),
        ):
            with self.subTest(argument=argument):
                editor = self.editor(
                    "app = Application()\napp.withRouting(\n"
                    f"    {argument}  # Keep\n)\n",
                )
                result = editor.routing(context, self.base / f"routes/{context}.py")
                calls = [
                    node for node in ast.walk(ast.parse(result))
                    if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "withRouting"
                ]
                call = calls[0]
                value = call.args[0] if call.args else call.keywords[0].value
                self.assertIsInstance(value, ast.Constant)
                self.assertIn(f"{argument},  # Keep", result)

    def test_single_line_empty_existing_trailing_comma_and_positional_calls(
        self,
    ) -> None:
        """
        Preserve empty, positional, and trailing comma call styles.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        for call in (
            "app.withRouting()",
            "app.withRouting(health='/up')",
            "app.withRouting(health='/up',)",
            "app.withRouting(None, None, None, '/up')",
        ):
            with self.subTest(call=call):
                editor = self.editor(f"app = Application()\n{call}\n")
                result = editor.routing("websocket", self.base / "routes/ws.py")
                self.assertValid(result)
                self.assertIn('websocket="routes/ws.py"', result)

    def test_replaces_disabled_contexts_only(self) -> None:
        """
        Replace disabled route contexts without changing other arguments.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        for value in ("None", "''", "[]", "()"):
            with self.subTest(value=value):
                editor = self.editor(
                    "app = Application()\n"
                    f"app.withRouting(api={value}, health='/up')\n",
                )
                result = editor.routing("api", self.base / "routes/api.py")
                self.assertIn('api="routes/api.py"', result)
                self.assertIn("health='/up'", result)
                self.assertValid(result)

    def test_updates_a_disabled_positional_context(self) -> None:
        """
        Enable a disabled positional route context without changing its peers.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "app = Application()\n"
            "app.withRouting(None, 'custom/web.py', health='/up')"
            "\n",
        )
        result = editor.routing("api", self.base / "routes/api.py")
        self.assertIn(
            'withRouting("routes/api.py", \'custom/web.py\', health=\'/up\')',
            result,
        )

    def test_preserves_literal_and_dynamic_custom_paths(self) -> None:
        """
        Preserve custom route paths expressed as literals or dynamic values.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        values = [
            "'custom/api.py'",
            "['first.py', 'second.py']",
            "custom_routes",
            "choose_routes()",
        ]
        for value in values:
            with self.subTest(value=value):
                editor = self.editor(
                    f"app = Application()\napp.withRouting(api={value})\n",
                )
                self.assertIsNone(editor.routing("api", self.base / "routes/api.py"))
                self.assertEqual(self.path.read_bytes(), editor._original)

    def test_reads_static_paths_and_reports_dynamic_values(self) -> None:
        """
        Read static route paths and identify unresolved dynamic values.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "app = Application()\n"
            "app.withRouting(api=['a.py', 'b.py'], ai=settings.ai"
            ")\n",
        )
        self.assertEqual(editor.routePaths("api"), ["a.py", "b.py"])
        self.assertIsNone(editor.routePaths("ai"))
        self.assertEqual(editor.routePaths("console"), [])

    def test_expanded_routing_reports_dynamic_paths(self) -> None:
        """
        Defer expanded route dictionaries to the application's loaded values.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor("app = Application()\napp.withRouting(**ROUTES)\n")
        self.assertIsNone(editor.routePaths("api"))
        self.assertIsNone(editor.routing(
            "api", self.base / "custom/api.py", registered=True,
        ))
        with self.assertRaises(BootstrapEditError):
            editor.routing("api", self.base / "custom/api.py")

    def test_explicit_disabled_context_is_not_an_unresolved_expansion(self) -> None:
        """
        Keep explicit None arguments separate from missing expanded contexts.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "app = Application()\napp.withRouting(api=None, **ROUTES)\n",
        )
        self.assertEqual(editor.routePaths("api"), [])

    def test_multiple_effective_paths_are_registered_together(self) -> None:
        """
        Retain every configured route file when adding a missing argument.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor("app = Application()\napp.withRouting(health='/up')\n")
        result = editor.routing(
            "api",
            [self.base / "custom/one.py", self.base / "custom/two.py"],
        )
        editor.commit(result)
        updated = BootstrapEditor(self.path, self.base)
        self.assertEqual(updated.routePaths("api"), ["custom/one.py", "custom/two.py"])
        self.assertTrue(updated.hasRouting)

    def test_generated_route_literals_use_double_quotes(self) -> None:
        """
        Use double quotes for every inserted routing string literal.

        Returns
        -------
        None
            Complete quote, path-value, and idempotence assertions.
        """
        # Check replacement, appended, list, and newly created registrations.
        for call in (
            "",
            "app.withRouting()\n",
            'app.withRouting(health="/up")\n',
            'app.withRouting(\n    health="/up",\n)\n',
            'app.withRouting(None, health="/up")\n',
        ):
            for multiple in (False, True):
                with self.subTest(call=call, multiple=multiple):
                    editor = self.editor(f"app = Application()\n{call}app.create()\n")
                    paths = [self.base / "routes/one.py", self.base / "routes/two.py"]
                    result = editor.routing("api", paths if multiple else paths[0])
                    tokens = tokenize.generate_tokens(io.StringIO(result).readline)
                    literals = [
                        token.string for token in tokens
                        if token.type == tokenize.STRING
                    ]
                    self.assertTrue(literals)
                    self.assertTrue(all(value.startswith('"') for value in literals))
                    editor.commit(result)
                    updated = BootstrapEditor(self.path, self.base)
                    expected = ["routes/one.py", "routes/two.py"]
                    self.assertEqual(
                        updated.routePaths("api"),
                        expected if multiple else expected[:1],
                    )
                    self.assertIsNone(updated.routing("api", paths))

    def test_escaped_paths_preserve_source_encoding_and_literal_values(self) -> None:
        """
        Preserve special path characters under source coding cookies and BOMs.

        Returns
        -------
        None
            Complete literal round-trip and source-metadata assertions.
        """
        # Escape Unicode separators, quotes, and control characters safely.
        paths = [
            self.base / "routes" / "café's \"route\"\n\t\u2028.py",
            self.base / "routes" / "back\\slash.py",
        ]
        source = "app = Application()\napp.create()\n"
        for content in (
            ("# coding: latin-1\n# café\n" + source).encode("latin-1"),
            codecs.BOM_UTF8 + ("# café\n" + source).encode("utf-8"),
        ):
            with self.subTest(content=content):
                self.path.write_bytes(content)
                editor = BootstrapEditor(self.path, self.base)
                result = editor.routing("api", paths)
                editor.commit(result)
                updated = BootstrapEditor(self.path, self.base)
                self.assertEqual(
                    updated.routePaths("api"),
                    [
                        path.resolve().relative_to(self.base).as_posix()
                        for path in paths
                    ],
                )
                header = content.split(b"app =", 1)[0]
                self.assertTrue(self.path.read_bytes().startswith(header))
                self.assertIsNone(updated.routing("api", paths))

    def test_reports_missing_direct_routing_registration(self) -> None:
        """
        Expose whether the source contains a directly editable route call.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor("app = Application()\nconfigure(app)\napp.create()\n")
        self.assertFalse(editor.hasRouting)

    def test_missing_registration_precedes_create_and_keeps_its_comment(self) -> None:
        """
        Insert missing routing before creation and retain its leading comment.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "app = Application()\n"
            "app.withPaths(paths)\n"
            "# Initialize here.\n"
            "app.create()\n",
        )
        result = editor.routing("api", self.base / "routes/api.py")
        self.assertIn(
            (
                "app.withPaths(paths)\n"
                'app.withRouting(api="routes/api.py")\n'
                "\n"
                "# Initialize here.\n"
                "app.create()"
            ),
            result,
        )
        self.assertValid(result)

    def test_chained_creation_registers_routes_before_create(self) -> None:
        """
        Insert routing before a chained application initialization.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "app = (\n    Application().withProviders(Provider)\n    .create()\n)\n",
        )
        result = editor.routing("console", self.base / "routes/console.py")
        self.assertIn(
            (
                '.withProviders(Provider).withRouting(console="routes'
                '/console.py")\n'
                "    .create()"
            ),
            result,
        )
        self.assertValid(result)

    def test_only_effective_last_routing_registration_is_updated(self) -> None:
        """
        Update the final routing call while preserving earlier calls.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "app = Application()\n"
            "app.withRouting(api='old.py')\n"
            "app.withRouting(health='/up')\n"
            "app.create()\n",
        )
        result = editor.routing("api", self.base / "routes/new.py")
        self.assertIn("app.withRouting(api='old.py')", result)
        self.assertIn('app.withRouting(health=\'/up\', api="routes/new.py")', result)

    def test_alias_application_and_factory_return_are_supported(self) -> None:
        """
        Support application import aliases and factory return registration.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "from orionis import Application as Orionis\n"
            "def build():\n"
            "    application = Orionis()\n"
            "    application.withProviders(Provider)\n"
            "    return application.create()\n"
            "app = build()\n",
        )
        result = editor.routing("ai", self.base / "routes/ai.py")
        self.assertIn(
            (
                '    application.withRouting(ai="routes/ai.py")\n'
                "\n"
                "    return application.create()"
            ),
            result,
        )
        self.assertValid(result)

    def test_module_application_import_is_supported(self) -> None:
        """
        Support application construction through an imported module alias.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "import orionis as framework\n"
            "app = framework.Application()\napp.create()\n",
        )
        self.assertValid(editor.routing("web", self.base / "routes/web.py"))

    def test_unrelated_nested_builder_calls_do_not_become_application_create(
        self,
    ) -> None:
        """
        Ignore create calls passed as constructor arguments.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor("app = Application(cache=cache.create())\napp.create()\n")
        result = editor.routing("api", self.base / "routes/api.py")
        self.assertIn("cache=cache.create()", result)
        self.assertLess(result.index("withRouting"), result.rindex("app.create()"))

    def test_lifespan_adds_import_and_callback_once_before_create(self) -> None:
        """
        Import and register lifespan callbacks exactly once before creation.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            '"""Bootstrap documentation."""\n'
            "from __future__ import annotations\n"
            "from orionis import Application\n"
            "app = Application()\n"
            "# Boot application.\n"
            "app.create()\n",
        )
        result = editor.lifespan(self.base / "bootstrap/lifespan.py")
        self.assertValid(result)
        self.assertTrue(
            result.startswith(
                '"""Bootstrap documentation."""\nfrom __future__ import annotations\n',
            ),
        )
        self.assertEqual(
            result.count("from bootstrap.lifespan import register_lifespan_callbacks"),
            1,
        )
        self.assertLess(
            result.index("register_lifespan_callbacks(app)"),
            result.index("# Boot application."),
        )
        editor.commit(result)
        self.assertIsNone(
            BootstrapEditor(self.path, self.base).lifespan(
                self.base / "bootstrap/lifespan.py",
            ),
        )

    def test_lifespan_import_extends_existing_group_without_blank_lines(self) -> None:
        """
        Extend multiline imports while preserving groups and attached comments.

        Returns
        -------
        None
            Complete import-layout and bootstrap-syntax assertions.
        """
        # Retain headers, grouping, inline comments, and application comments.
        source = (
            "#!/usr/bin/env python\n"
            "# coding: utf-8\n"
            '"""Bootstrap documentation."""\n'
            "from __future__ import annotations\n"
            "\n"
            "from orionis import Application\n"
            "\n"
            "# Keep local imports together.\n"
            "from app.providers import (\n"
            "    Provider,\n"
            ")  # Provider registration.\n"
            "\n"
            "# Construct the configured application.\n"
            "app = Application()\n"
            "app.create()\n"
        )
        editor = self.editor(source)
        result = editor.lifespan(self.base / "bootstrap/lifespan.py")
        imported = "from bootstrap.lifespan import register_lifespan_callbacks\n"
        self.assertIn(
            ")  # Provider registration.\n" + imported
            + "\n# Construct the configured application.\n",
            result,
        )
        self.assertTrue(result.startswith(source[:source.index("# Keep local")]))
        self.assertValid(result)

    def test_factory_lifespan_import_extends_local_import_group(self) -> None:
        """
        Extend factory imports without separating them or moving module imports.

        Returns
        -------
        None
            Complete local-scope, comment, and indentation assertions.
        """
        # Append to local imports before intervening factory preparation.
        editor = self.editor(
            "from orionis import Application\n"
            "\n"
            "def build():\n"
            '    """Build the application."""\n'
            "    from app.providers import (\n"
            "        Provider,\n"
            "    )  # Preserve provider imports.\n"
            "\n"
            "    prepare(Provider)\n"
            "    # Preserve the application comment.\n"
            "    app = Application()\n"
            "    return app.create()\n",
        )
        result = editor.lifespan(self.base / "bootstrap/lifespan.py")
        self.assertIn(
            "    )  # Preserve provider imports.\n"
            "    from bootstrap.lifespan import register_lifespan_callbacks\n"
            "\n    prepare(Provider)\n",
            result,
        )
        self.assertIn(
            "    # Preserve the application comment.\n    app = Application()",
            result,
        )
        self.assertValid(result)

    def test_lifespan_import_preserves_headers_without_existing_imports(self) -> None:
        """
        Preserve coding cookies and shebangs when adding the first import.

        Returns
        -------
        None
            Complete header-preservation and import-placement assertions.
        """
        # Keep encoding declarations in Python's first two physical lines.
        header = "#!/usr/bin/env python\n# coding: latin-1\n# café\n"
        self.path.write_bytes(
            (header + "app = Application()\napp.create()\n").encode("latin-1"),
        )
        editor = BootstrapEditor(self.path, self.base)
        result = editor.lifespan(self.base / "bootstrap/lifespan.py")
        editor.commit(result)
        self.assertTrue(self.path.read_bytes().startswith(header.encode("latin-1")))
        self.assertIn(
            "from bootstrap.lifespan import register_lifespan_callbacks\n\napp =",
            result,
        )

    def test_lifespan_import_follows_docstrings_and_future_imports(self) -> None:
        """
        Keep callback imports after module docstrings and future declarations.

        Returns
        -------
        None
            Complete future-import ordering and valid-syntax assertions.
        """
        # Preserve Python's required future-import location.
        header = (
            '"""Bootstrap documentation."""\n'
            "from __future__ import annotations\n"
        )
        editor = self.editor(header + "\napp = Application()\napp.create()\n")
        result = editor.lifespan(self.base / "bootstrap/lifespan.py")
        self.assertTrue(result.startswith(
            header + "\nfrom bootstrap.lifespan import register_lifespan_callbacks\n",
        ))
        self.assertValid(result)

    def test_lifespan_splits_terminal_chained_create_preserving_builder(self) -> None:
        """
        Split terminal creation to register callbacks after builder setup.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "from orionis import Application\n"
            "app = (\n"
            "    Application()\n"
            "    .withRouting(health='/up')\n"
            "    .withProviders(Provider)\n"
            "    .create()\n"
            ")\n",
        )
        result = editor.lifespan(self.base / "bootstrap/lifespan.py")
        self.assertValid(result)
        self.assertIn(".withProviders(Provider)", result)
        self.assertLess(
            result.index("app = ("),
            result.index("register_lifespan_callbacks(app)"),
        )
        self.assertLess(
            result.index("register_lifespan_callbacks(app)"),
            result.index("app.create()"),
        )

    def test_factory_reuses_module_level_lifespan_alias(self) -> None:
        """
        Reuse an existing module-level lifespan callback alias inside factories.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "from bootstrap.lifespan import register_lifespan_cal"
            "lbacks as callbacks\n"
            "def build():\n"
            "    app = Application()\n"
            "    callbacks(app)\n"
            "    return app.create()\n",
        )
        self.assertIsNone(editor.lifespan(self.base / "bootstrap/lifespan.py"))

    def test_lifespan_recognizes_module_alias_call(self) -> None:
        """
        Recognize existing lifespan registration through a module alias.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "import bootstrap.lifespan as lifecycle\n"
            "app = Application()\n"
            "lifecycle.register_lifespan_callbacks(app)\n"
            "app.create()\n",
        )
        self.assertIsNone(editor.lifespan(self.base / "bootstrap/lifespan.py"))

    def test_relative_and_package_imports_remain_idempotent(self) -> None:
        """
        Recognize relative callback imports and package module aliases.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        for imported, callback in (
            (
                "from .lifespan import register_lifespan_callbacks as callbacks",
                "callbacks",
            ),
            (
                "from bootstrap import lifespan as lifecycle",
                "lifecycle.register_lifespan_callbacks",
            ),
        ):
            with self.subTest(imported=imported):
                source = (
                    f"{imported}\napp = Application()\n{callback}(app)\napp.create()\n"
                )
                editor = self.editor(source)
                self.assertIsNone(editor.lifespan(self.base / "bootstrap/lifespan.py"))

    def test_conditional_import_does_not_supply_the_new_registration(self) -> None:
        """
        Import an executable callback instead of reusing TYPE_CHECKING imports.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "if TYPE_CHECKING:\n"
            "    from bootstrap.lifespan import register_lifespan_callbacks\n"
            "app = Application()\napp.create()\n",
        )
        result = editor.lifespan(self.base / "bootstrap/lifespan.py")
        self.assertIn("_orionis_lifespan_1(app)", result)
        self.assertValid(result)

    def test_late_import_does_not_get_called_before_it_is_bound(self) -> None:
        """
        Use a new import when the existing callback import follows create.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "app = Application()\napp.create()\n"
            "from bootstrap.lifespan import register_lifespan_callbacks\n",
        )
        result = editor.lifespan(self.base / "bootstrap/lifespan.py")
        self.assertIn("_orionis_lifespan_1(app)", result)
        self.assertLess(
            result.index("_orionis_lifespan_1(app)"), result.index("app.create()"),
        )

    def test_lifespan_uses_existing_import_alias_when_call_is_missing(self) -> None:
        """
        Reuse a callback import alias when inserting missing registration.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "from bootstrap.lifespan import register_lifespan_cal"
            "lbacks as callbacks\n"
            "app = Application()\n"
            "app.create()\n",
        )
        result = editor.lifespan(self.base / "bootstrap/lifespan.py")
        self.assertIn("callbacks(app)", result)
        self.assertEqual(result.count("from bootstrap.lifespan"), 1)

    def test_keyword_callback_argument_is_not_duplicated(self) -> None:
        """
        Recognize explicit keyword application arguments in existing calls.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "from bootstrap.lifespan import register_lifespan_callbacks\n"
            "app = Application()\nregister_lifespan_callbacks(app=app)\napp.create()\n",
        )
        self.assertIsNone(editor.lifespan(self.base / "bootstrap/lifespan.py"))

    def test_custom_registration_is_preserved(self) -> None:
        """
        Preserve custom lifespan callback registration.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "from project.callbacks import register_lifespan_call"
            "backs as custom_callbacks\n"
            "app = Application()\n"
            "custom_callbacks(app)\n"
            "app.create()\n",
        )
        self.assertIsNone(editor.lifespan(self.base / "bootstrap/lifespan.py"))

    def test_lifespan_name_collision_gets_a_fresh_alias(self) -> None:
        """
        Choose a fresh lifespan callback alias when the default name is bound.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "from other import register_lifespan_callbacks\n"
            "app = Application()\n"
            "app.create()\n",
        )
        result = editor.lifespan(self.base / "bootstrap/lifespan.py")
        self.assertIn("from other import register_lifespan_callbacks", result)
        self.assertIn(
            (
                "from bootstrap.lifespan import register_lifespan_cal"
                "lbacks as _orionis_lifespan_1"
            ),
            result,
        )
        self.assertIn("_orionis_lifespan_1(app)", result)
        self.assertValid(result)

    def test_factory_lifespan_import_and_registration_keep_indentation(self) -> None:
        """
        Preserve factory indentation when importing and registering callbacks.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor("def build():\n    app = Application()\n    return app\n")
        result = editor.lifespan(self.base / "bootstrap/lifespan.py")
        self.assertIn(
            "    from bootstrap.lifespan import register_lifespan_callbacks",
            result,
        )
        self.assertIn("    register_lifespan_callbacks(app)", result)
        self.assertValid(result)

    def test_utf8_columns_and_comments_are_preserved(self) -> None:
        """
        Preserve Unicode text and comments while locating AST source columns.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "app = Application()\napp.withRouting(health='/salud/ñ')  # español\n",
        )
        result = editor.routing("api", self.base / "routes/api.py")
        self.assertIn('health=\'/salud/ñ\', api="routes/api.py")  # español', result)
        self.assertValid(result)

    def test_encoding_bom_and_crlf_are_preserved_on_commit(self) -> None:
        """
        Preserve the original BOM and CRLF newlines when committing edits.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        source = "# español\r\napp = Application()\r\napp.create()\r\n"
        self.path.write_bytes(codecs.BOM_UTF8 + source.encode("utf-8"))
        editor = BootstrapEditor(self.path, self.base)
        editor.commit(editor.routing("api", self.base / "routes/api.py"))
        content = self.path.read_bytes()
        self.assertTrue(content.startswith(codecs.BOM_UTF8))
        self.assertEqual(content.count(b"\n"), content.count(b"\r\n"))
        self.assertIn("# español".encode(), content)

    def test_non_utf8_coding_cookie_is_preserved(self) -> None:
        """
        Preserve a non-UTF-8 coding cookie and its encoded source content.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        self.path.write_bytes(
            "# coding: latin-1\n# café\napp = Application()\napp.create()\n".encode(
                "latin-1",
            ),
        )
        editor = BootstrapEditor(self.path, self.base)
        editor.commit(editor.routing("api", self.base / "routes/api.py"))
        self.assertIn("# café".encode("latin-1"), self.path.read_bytes())

    def test_second_commit_is_skipped_and_concurrent_changes_are_preserved(
        self,
    ) -> None:
        """
        Preserve edits made by the developer after planning.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor("app = Application()\napp.create()\n")
        result = editor.routing("api", self.base / "routes/api.py")
        self.path.write_text("# Developer changed this file.\n", encoding="utf-8")
        with self.assertRaises(BootstrapEditError):
            editor.commit(result)
        self.assertEqual(self.path.read_text(), "# Developer changed this file.\n")
        self.assertEqual(list(self.path.parent.glob(".bootstrap-*")), [])

    def test_missing_final_newline_is_handled(self) -> None:
        """
        Insert routing after source that lacks a final newline.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor("app = Application()")
        result = editor.routing("console", self.base / "routes/console.py")
        self.assertValid(result)
        self.assertIn("Application()\n", result)

    def test_ambiguous_or_conditional_application_is_rejected(self) -> None:
        """
        Reject ambiguous or conditional application construction.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        for source in (
            "one = Application()\ntwo = Application()\n",
            "if enabled:\n    app = Application()\n",
            "app = Application()\napp = unknown()\n",
        ):
            with self.subTest(source=source), self.assertRaises(BootstrapEditError):
                self.editor(source)

    def test_conditional_registration_and_dynamic_kwargs_fail_without_writes(
        self,
    ) -> None:
        """
        Reject ambiguous routing calls before writing anything.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        for source in (
            "app = Application()\nif enabled:\n    app.withRouting()\n",
            "app = Application()\napp.withRouting(**settings)\n",
            "app = Application()\napp.withRouting(*settings)\n",
        ):
            with self.subTest(source=source):
                editor = self.editor(source)
                with self.assertRaises(BootstrapEditError):
                    editor.routing("api", self.base / "routes/api.py")
                self.assertEqual(self.path.read_text(), source)

    def test_routing_after_create_is_rejected(self) -> None:
        """
        Reject routing configuration after application creation.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "app = Application()\napp.create()\napp.withRouting(health='/up')\n",
        )
        with self.assertRaises(BootstrapEditError):
            editor.routing("api", self.base / "routes/api.py")

    def test_later_helper_routing_is_rejected_before_any_write(self) -> None:
        """
        Prevent helper routing from overwriting a newly inserted context.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        for invocation in ("configure(app)", "configure(application=app)"):
            with self.subTest(invocation=invocation):
                source = (
                    "def configure(application):\n"
                    "    application.withRouting(web='routes/web.py', health='/up')\n"
                    "app = Application()\n"
                    "app.withRouting(web='routes/web.py', health='/up')\n"
                    f"{invocation}\napp.create()\n"
                )
                editor = self.editor(source)
                with self.assertRaisesRegex(BootstrapEditError, "Helper configure"):
                    editor.routing("api", self.base / "routes/api.py")
                self.assertEqual(self.path.read_text(), source)

    def test_outer_helper_runs_after_its_routing_argument(self) -> None:
        """
        Account for Python argument evaluation when a helper encloses routing.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "def configure(application):\n"
            "    application.withRouting(web='routes/web.py')\n"
            "app = Application()\n"
            "configure(app.withRouting(health='/up'))\napp.create()\n",
        )
        with self.assertRaisesRegex(BootstrapEditError, "Helper configure"):
            editor.routing("api", self.base / "routes/api.py")

    def test_registered_expansion_does_not_bypass_helper_guard(self) -> None:
        """
        Run source safety checks even when runtime confirms an expanded route.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "def configure(application):\n"
            "    application.withRouting(web='routes/web.py')\n"
            "app = Application()\napp.withRouting(**ROUTES)\n"
            "configure(app)\napp.create()\n",
        )
        with self.assertRaisesRegex(BootstrapEditError, "Helper configure"):
            editor.routing("api", self.base / "routes/api.py", registered=True)

    def test_helper_routing_before_the_selected_call_is_safe(self) -> None:
        """
        Edit the final direct call when it follows helper configuration.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "def configure(application):\n"
            "    application.withRouting(web='routes/web.py')\n"
            "app = Application()\nconfigure(app)\n"
            "app.withRouting(web='routes/web.py', health='/up')\napp.create()\n",
        )
        self.assertValid(editor.routing("api", self.base / "routes/api.py"))

    def test_helper_called_with_another_receiver_is_safe(self) -> None:
        """
        Ignore mutations of an object other than the selected application.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "def configure(application):\n"
            "    application.withRouting(web='routes/web.py')\n"
            "app = Application()\napp.withRouting(health='/up')\n"
            "configure(other)\napp.create()\n",
        )
        self.assertValid(editor.routing("api", self.base / "routes/api.py"))

    def test_lifespan_helper_does_not_prevent_route_registration(self) -> None:
        """
        Accept ordinary callback helpers that only register lifespan events.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "def register_lifespan_callbacks(application):\n"
            "    application.on(event, callback)\n"
            "app = Application()\napp.withRouting(health='/up')\n"
            "register_lifespan_callbacks(app)\napp.create()\n",
        )
        self.assertValid(editor.routing("api", self.base / "routes/api.py"))

    def test_factory_helper_routing_is_rejected(self) -> None:
        """
        Bind factory application names to module helper parameters.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "def configure(application):\n"
            "    application.withRouting(web='routes/web.py')\n"
            "def build():\n"
            "    instance = Application()\n"
            "    instance.withRouting(health='/up')\n"
            "    configure(application=instance)\n"
            "    return instance.create()\n",
        )
        with self.assertRaisesRegex(BootstrapEditError, "Helper configure"):
            editor.routing("api", self.base / "routes/api.py")

    def test_helper_closure_over_the_application_is_rejected(self) -> None:
        """
        Recognize helper routing through a local application closure.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "def build():\n"
            "    instance = Application()\n"
            "    instance.withRouting(health='/up')\n"
            "    def configure():\n"
            "        instance.withRouting(web='routes/web.py')\n"
            "    configure()\n"
            "    return instance.create()\n",
        )
        with self.assertRaisesRegex(BootstrapEditError, "Helper configure"):
            editor.routing("api", self.base / "routes/api.py")

    def test_helper_global_name_does_not_capture_a_factory_local(self) -> None:
        """
        Keep module helper globals separate from equally named factory locals.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "def configure():\n"
            "    app.withRouting(web='routes/web.py')\n"
            "def build():\n"
            "    app = Application()\n"
            "    app.withRouting(health='/up')\n"
            "    configure()\n"
            "    return app.create()\n",
        )
        self.assertValid(editor.routing("api", self.base / "routes/api.py"))

    def test_conditional_application_rebinding_is_rejected(self) -> None:
        """
        Refuse ambiguous reassignment before selecting a routing receiver.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        with self.assertRaises(BootstrapEditError):
            self.editor(
                "app = Application()\n"
                "app.withRouting(health='/up')\n"
                "if enabled:\n    app = other\n"
                "app.create()\n",
            )

    def test_conditional_helper_parameter_rebind_cannot_hide_route_mutation(
        self,
    ) -> None:
        """
        Reject routing that can still receive the original app after a branch.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "def configure(application):\n"
            "    if enabled:\n        application = other\n"
            "    application.withRouting(web='routes/web.py')\n"
            "app = Application()\napp.withRouting(health='/up')\n"
            "configure(app)\napp.create()\n",
        )
        with self.assertRaisesRegex(BootstrapEditError, "Helper configure"):
            editor.routing("api", self.base / "routes/api.py")

    def test_helper_local_binding_is_separate_from_application_closure(self) -> None:
        """
        Avoid treating a helper-local name as the application's global.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "def configure():\n"
            "    app = other\n"
            "    app.withRouting(web='routes/web.py')\n"
            "app = Application()\napp.withRouting(health='/up')\n"
            "configure()\napp.create()\n",
        )
        self.assertValid(editor.routing("api", self.base / "routes/api.py"))

    def test_conditional_factory_returns_are_rejected(self) -> None:
        """
        Reject registration around conditional application factory returns.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor(
            "def build():\n"
            "    app = Application()\n"
            "    if early:\n"
            "        return app\n"
            "    return app.create()\n",
        )
        with self.assertRaises(BootstrapEditError):
            editor.lifespan(self.base / "bootstrap/lifespan.py")

    def test_external_or_invalid_lifespan_import_paths_are_rejected(self) -> None:
        """
        Reject lifespan modules outside the root or with invalid import names.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor("app = Application()\napp.create()\n")
        for path in (
            self.base.parent / "outside.py",
            self.base / "invalid-name/lifespan.py",
        ):
            with self.subTest(path=path), self.assertRaises(BootstrapEditError):
                editor.lifespan(path)

    def test_generated_bootstrap_executes_in_the_correct_order(self) -> None:
        """
        Execute generated routing before application initialization.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.

        class Application:
            def __init__(self) -> None:
                """
                Initialize the application test double event log.

                Returns
                -------
                None
                    Store an empty list of configuration events.
                """
                # Track the order in which the generated bootstrap runs.
                self.events = []

            def withRouting(self, **kwargs: object) -> Application:
                """
                Record a routing configuration event.

                Parameters
                ----------
                kwargs : object
                    Routing keyword arguments supplied by the bootstrap.

                Returns
                -------
                Application
                    Return this application instance for fluent calls.
                """
                # Record routing arguments before initialization.
                self.events.append(("routing", kwargs))
                return self

            def create(self) -> Application:
                """
                Record application initialization.

                Returns
                -------
                Application
                    Return this application instance for fluent calls.
                """
                # Record initialization after the routing setup.
                self.events.append(("created", None))
                return self

        editor = self.editor("app = Application().create()\n")
        result = editor.routing("api", self.base / "routes/api.py")
        namespace = {"Application": Application}
        exec(  # noqa: S102 - Verify generated application code.
            compile(result, str(self.path), "exec"), namespace,
        )
        self.assertEqual(
            namespace["app"].events,
            [("routing", {"api": "routes/api.py"}), ("created", None)],
        )

    def test_modified_calls_have_unique_keyword_names(self) -> None:
        """
        Keep keyword argument names unique after routing edits.

        Returns
        -------
        None
            Complete the assertions without returning a value.
        """
        # Exercise the bootstrap edit and verify the expected source.
        editor = self.editor("app = Application()\napp.withRouting(health='/up')\n")
        result = editor.routing("api", self.base / "routes/api.py")
        calls = [
            n
            for n in ast.walk(ast.parse(result))
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        ]
        for call in calls:
            names = [kw.arg for kw in call.keywords]
            self.assertEqual(len(names), len(set(names)))
