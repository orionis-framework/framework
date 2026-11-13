# ruff: noqa: ANN202, PLC0415, PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Keep runtime reflection annotations and intentionally deferred imports.
"""Verify the documentation model against the syntax used by the framework."""

import ast
import contextlib
import io
import unittest
from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory


@unittest.skipUnless(find_spec("pydoctor"), "Install the docs dependency group")
class TestDocumentationSystem(unittest.TestCase):
    """Exercise real pydoctor parsing and documentation-coverage diagnostics."""

    def _buildSystem(self, source: str | dict[str, str]):
        """Parse an isolated module with the production documentation system.

        Parameters
        ----------
        source : str or dict[str, str]
            Module source, or package filenames mapped to source text.

        Returns
        -------
        tuple
            Built documentation system and captured diagnostic output.
        """
        from pydoctor.options import Options  # pyright: ignore[reportMissingImports]
        from resources.docs.pydoctor.system import DocumentationSystem

        with TemporaryDirectory() as directory:
            if isinstance(source, str):
                path = Path(directory) / "example.py"
                path.write_text(source, encoding="utf-8")
            else:
                path = Path(directory) / "example"
                path.mkdir()
                for filename, content in source.items():
                    (path / filename).write_text(content, encoding="utf-8")
            system = DocumentationSystem(Options.defaults())
            builder = system.systemBuilder(system)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                builder.addModule(path)
                builder.buildModules()
            return system, output.getvalue()

    def testAnnotatedMetadataIsPreserved(self) -> None:
        """Keep validation messages and literal choices out of type-name parsing.

        Returns
        -------
        None
            Confirm that metadata remains present without annotation errors.
        """
        system, diagnostics = self._buildSystem('''"""Example schema."""
from typing import Annotated as Field, Literal as Choice
class Payload:
    """Input accepted by the example endpoint."""
    token: Field[str, "not a Python type!", {"description": "token value"}]
    """Token supplied by the caller."""
    mode: Choice["read-only", "write-only"]
    """Operation mode selected by the caller."""
''')
        self.assertEqual(system.violations, 0, diagnostics)
        annotation = ast.unparse(system.allobjects["example.Payload.token"].annotation)
        self.assertIn("not a Python type!", annotation)
        self.assertIn("token value", annotation)

    def testModernTypeAliasesAreDocumented(self) -> None:
        """Include PEP 695 aliases in the model and retain their descriptions.

        Returns
        -------
        None
            Confirm that aliases have a target, a value and source documentation.
        """
        system, diagnostics = self._buildSystem('''"""Example type aliases."""
type Row = dict[str, int]
"""Mapping from column names to integer values."""
type Rows[T] = tuple[T, ...]
"""Immutable sequence of row values."""
class Response:
    """Example HTTP response."""
type HttpResponse = Response
"""Response accepted as a handler result."""
''')
        self.assertEqual(system.violations, 0, diagnostics)
        alias = system.allobjects["example.Row"]
        self.assertEqual(alias.kind.name, "TYPE_ALIAS")
        self.assertEqual(ast.unparse(alias.value), "dict[str, int]")
        self.assertIn("column names", alias.docstring)
        self.assertIn("example.Rows", system.allobjects)
        response_alias = system.allobjects["example.HttpResponse"]
        self.assertEqual(response_alias.kind.name, "TYPE_ALIAS")
        self.assertEqual(ast.unparse(response_alias.value), "Response")
        self.assertIn("handler result", response_alias.docstring)

    def testNumpyAttributesCountAsDocumented(self) -> None:
        """Recognize field documentation without duplicate inline docstrings.

        Returns
        -------
        None
            Keep NumPy Attributes visible to the undocumented-object index.
        """
        from pydoctor.templatewriter.summary import hasdocstring  # pyright: ignore[reportMissingImports]

        system, diagnostics = self._buildSystem('''"""Example configuration."""
class Config:
    """Configure the example service.

    Attributes
    ----------
    limit : int
        Maximum number of accepted items.
    """
    limit: int = 10
''')
        self.assertEqual(system.violations, 0, diagnostics)
        field = system.allobjects["example.Config.limit"]
        self.assertTrue(hasdocstring(field))
        self.assertIsNotNone(field.parsed_docstring)
        self.assertIn("Maximum number", field.docstring)

    def testNumpyFieldsInferTypesFromSourceAnnotations(self) -> None:
        """Retain types when NumPy field descriptions omit redundant type names.

        Returns
        -------
        None
            Confirm constructor parameters and instance attributes stay typed.
        """
        from pydoctor import epydoc2stan  # pyright: ignore[reportMissingImports]
        from pydoctor.stanutils import flatten  # pyright: ignore[reportMissingImports]
        from pydoctor.templatewriter.summary import hasdocstring  # pyright: ignore[reportMissingImports]

        system, diagnostics = self._buildSystem('''"""Example configuration."""
class Config:
    """Configure the example service.

    Attributes
    ----------
    _limit
        Maximum number of accepted items.
    """
    def __init__(self, limit: int) -> None:
        """Store the configured limit.

        Parameters
        ----------
        limit
            Maximum number of accepted items.

        Returns
        -------
        ``None``
            Initialize this configuration.
        """
        self._limit: int = limit
''')
        self.assertEqual(system.violations, 0, diagnostics)
        field = system.allobjects["example.Config._limit"]
        self.assertTrue(hasdocstring(field))
        self.assertEqual(epydoc2stan.get_parsed_type(field).to_text(), "int")
        rendered = flatten(
            epydoc2stan.format_docstring(
                system.allobjects["example.Config.__init__"],
            ),
        )
        self.assertIn('class="fieldArg">limit:</span><code>int</code>', rendered)
        self.assertIn("Maximum number of accepted items.", rendered)
        self.assertNotIn('class="undocumented"', rendered)
        self.assertEqual(system.violations, 0)

    def testMissingDocumentationRemainsAnError(self) -> None:
        """Reject visible objects that have no source or inherited documentation.

        Returns
        -------
        None
            Ensure the build cannot silently publish undocumented API members.
        """
        system, diagnostics = self._buildSystem('''"""Example module."""
def missing():
    pass
''')
        self.assertGreater(system.violations, 0)
        self.assertIn("Missing API documentation", diagnostics)

    def testInvalidTypeReferencesRemainErrors(self) -> None:
        """Continue reporting malformed forward references in genuine type positions.

        Returns
        -------
        None
            Ensure metadata support does not suppress annotation syntax errors.
        """
        system, diagnostics = self._buildSystem('''"""Example invalid annotation."""
value: "not a valid type!"
"""Value with an intentionally invalid type reference."""
''')
        self.assertGreater(system.violations, 0)
        self.assertIn("syntax error in annotation", diagnostics)

    def testSchemaPreparationTypesRenderWithoutUnavailableLinks(self) -> None:
        """Keep ellipses and external schema types literal in production docstrings.

        Returns
        -------
        None
            Reject unsupported link targets when rendering schema preparation docs.
        """
        from pydoctor import epydoc2stan, model  # pyright: ignore[reportMissingImports]
        from pydoctor.stanutils import flatten  # pyright: ignore[reportMissingImports]

        schemas = Path(__file__).resolve().parents[2] / "orionis" / "schemas"
        for filename in ("coercion.py", "instance_payload.py"):
            with self.subTest(module=filename):
                system, diagnostics = self._buildSystem(
                    (schemas / filename).read_text(encoding="utf-8"),
                )
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    for obj in system.allobjects.values():
                        if isinstance(obj, model.Function):
                            flatten(epydoc2stan.format_docstring(obj))
                diagnostics += output.getvalue()
                for target in ("...", "msgspec.Struct"):
                    self.assertNotIn(
                        f'Cannot find link target for "{target}"',
                        diagnostics,
                    )

    def testCaseInsensitivePageNamesRemainDistinct(self) -> None:
        """Keep a re-exported class from overwriting its module on Windows.

        Returns
        -------
        None
            Confirm that member links use the disambiguated module filename.
        """
        system, diagnostics = self._buildSystem(
            {
                "__init__.py": '''"""Example package."""
from .widget import Widget
__all__ = ["Widget"]
''',
                "widget.py": '''"""Widget utilities."""
LIMIT = 10
"""Maximum number of widgets."""
class Widget:
    """Example widget."""
''',
            },
        )
        self.assertEqual(system.violations, 0, diagnostics)
        module = system.allobjects["example.widget"]
        widget = system.allobjects["example.Widget"]
        self.assertNotEqual(module.url.casefold(), widget.url.casefold())
        self.assertTrue(module.url.endswith(".module.html"))
        self.assertEqual(
            system.allobjects["example.widget.LIMIT"].url,
            f"{module.url}#LIMIT",
        )

    def testRepeatedTocRenderingKeepsForwardLinks(self) -> None:
        """Reuse sidebar headings without dangling or duplicate backlink IDs.

        Returns
        -------
        None
            Confirm stable navigation and unlinked section titles.
        """
        from pydoctor import epydoc2stan  # pyright: ignore[reportMissingImports]
        from pydoctor.stanutils import flatten  # pyright: ignore[reportMissingImports]

        system, diagnostics = self._buildSystem('''"""Example module.

Lifecycle
---------
Start and stop the service.
"""
''')
        self.assertEqual(system.violations, 0, diagnostics)
        module = system.allobjects["example"]
        first = flatten(epydoc2stan.format_toc(module))
        second = flatten(epydoc2stan.format_toc(module))
        body = flatten(epydoc2stan.format_docstring(module))
        self.assertEqual(first, second)
        self.assertIn('href="#rst-lifecycle"', first)
        self.assertNotIn("toc-entry", first + body)
        self.assertIn('id="rst-lifecycle"', body)

    def testMissingReturnDescriptionRemainsAnError(self) -> None:
        """Reject return types whose NumPy descriptions are empty.

        Returns
        -------
        None
            Prevent undocumented return fields from reaching generated HTML.
        """
        system, diagnostics = self._buildSystem('''"""Example module."""
def ready() -> bool:
    """Check whether the service is ready.

    Returns
    -------
    bool
    """
    return True
''')
        self.assertGreater(system.violations, 0)
        self.assertIn("Missing return or yield description", diagnostics)

    def testYieldsDocumentsGeneratorWithoutEmptyReturnTable(self) -> None:
        """Retain generator signatures without inventing an undocumented return.

        Returns
        -------
        None
            Confirm NumPy Yields is complete documentation for generator output.
        """
        from pydoctor import epydoc2stan  # pyright: ignore[reportMissingImports]
        from pydoctor.stanutils import flatten  # pyright: ignore[reportMissingImports]

        system, diagnostics = self._buildSystem('''"""Example generator."""
from collections.abc import Iterator
def values(limit: int) -> Iterator[int]:
    """Yield each number below the limit.

    Parameters
    ----------
    limit : ``int``
        Exclusive upper bound.

    Yields
    ------
    ``int``
        Next number in ascending order.
    """
    yield from range(limit)
''')
        self.assertEqual(system.violations, 0, diagnostics)
        function = system.allobjects["example.values"]
        rendered = flatten(epydoc2stan.format_docstring(function))
        signature = epydoc2stan.get_parsed_signature(function).to_text()
        self.assertIn("Iterator[int]", signature)
        self.assertIn("Yields", rendered)
        self.assertNotIn("Returns", rendered)
        self.assertNotIn('class="undocumented"', rendered)
        self.assertEqual(system.violations, 0)


class TestDocumentationSite(unittest.TestCase):
    """Check generated HTML independently of pydoctor's diagnostic output."""

    def _validateSite(self, pages: dict[str, str]) -> dict[str, object]:
        """Validate a temporary collection of documentation pages.

        Parameters
        ----------
        pages : dict[str, str]
            Relative filenames mapped to HTML content.

        Returns
        -------
        dict[str, object]
            Site validation report.
        """
        from resources.docs.pydoctor.validate import validate_site

        with TemporaryDirectory() as directory:
            root = Path(directory)
            for filename, content in pages.items():
                (root / filename).write_text(content, encoding="utf-8")
            return validate_site(root)

    def testCompleteLocalNavigationPasses(self) -> None:
        """Accept existing pages, anchors and external references.

        Returns
        -------
        None
            Confirm that valid navigation produces no diagnostics.
        """
        report = self._validateSite(
            {
                "index.html": '<a href="widget.module.html#LIMIT">limit</a>',
                "widget.module.html": '<p id="LIMIT">Limit.</p><a href="https://example.com/">external</a>',
            },
        )
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["html_pages"], 2)

    def testIncompleteDocumentationAndBrokenLinksFail(self) -> None:
        """Reject missing descriptions, target files and target anchors.

        Returns
        -------
        None
            Ensure rendered documentation gaps block publication.
        """
        report = self._validateSite(
            {
                "index.html": """<span class="undocumented">Undocumented</span>
<a href="missing.html">missing file</a><a href="#missing">missing anchor</a>""",
            },
        )
        messages = "\n".join(report["errors"])
        self.assertIn("undocumented", messages)
        self.assertIn("missing local file", messages)
        self.assertIn("missing local anchor", messages)

    def testUrlCasingIsCheckedOnEveryPlatform(self) -> None:
        """Detect mismatched filenames even on case-insensitive filesystems.

        Returns
        -------
        None
            Keep navigation portable between Windows and static web hosts.
        """
        report = self._validateSite(
            {
                "index.html": '<a href="widget.html">widget</a>',
                "Widget.html": "<p>Widget.</p>",
            },
        )
        self.assertTrue(report["errors"])
        self.assertIn("missing local file", report["errors"][0])
