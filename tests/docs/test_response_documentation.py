# ruff: noqa: PLC0415, PT009
# Defer optional documentation dependencies and retain unittest assertions.
"""Verify production response documentation without reading generated files."""

from __future__ import annotations

import contextlib
import io
import unittest
from importlib.util import find_spec
from pathlib import Path

from tests.docs import test_pydoctor_system


@unittest.skipUnless(find_spec("pydoctor"), "Install the docs dependency group")
class TestResponseDocumentation(unittest.TestCase):
    """Check coverage and fluent return types in response documentation."""

    def testResponseTypesRenderWithoutUnqualifiedSelfLinks(
        self: TestResponseDocumentation,
    ) -> None:
        """Render fluent response methods with qualified return types.

        Returns
        -------
        None
            Verify constant coverage and reject unresolved bare Self references.
        """
        from pydoctor import epydoc2stan  # pyright: ignore[reportMissingImports]
        from pydoctor.stanutils import flatten  # pyright: ignore[reportMissingImports]

        source_path = (
            Path(__file__).resolve().parents[2] / "orionis" / "http" / "responses.py"
        )
        helper = test_pydoctor_system.TestDocumentationSystem()
        system, diagnostics = helper._buildSystem(  # noqa: SLF001
            source_path.read_text(encoding="utf-8"),
        )
        self.assertEqual(system.violations, 0, diagnostics)
        constant = system.allobjects["example._STATUS_CODE_TYPE_ERROR"]
        self.assertIsNotNone(constant.docstring)

        methods = (
            "Response.withStatusCode",
            "Response.withHeaders",
            "Response.withBackground",
            "RedirectResponse.withStatusCode",
        )
        for name in methods:
            with self.subTest(method=name):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    method = system.allobjects[f"example.{name}"]
                    rendered = flatten(epydoc2stan.format_docstring(method))
                self.assertNotIn(
                    'Cannot find link target for "Self"',
                    output.getvalue(),
                )
                self.assertIn("typing.Self", rendered)
