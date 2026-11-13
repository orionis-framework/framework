# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify filter output, independent builders, and Jinja escaping."""

from jinja2 import Environment
from orionis.test import TestCase
from orionis.view.filters import _filter_json, _filter_markdown


class TestJsonifyFilter(TestCase):
    """Check compact, formatted, and fallback representations."""

    def testSerializesSupportedValues(self) -> None:
        """Serialise each supported fixture to its exact compact JSON text.

        Returns
        -------
        None
            No return value.
        """
        cases = (
            ({"key": "value"}, '{"key":"value"}'),
            ([1, 2, 3], "[1,2,3]"),
            (None, "null"),
            (42, "42"),
            ({"a": 1}, '{"a":1}'),
            ("hello", '"hello"'),
            (0, "0"),
            ([], "[]"),
            (True, "true"),
            (False, "false"),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                result = _filter_json()(value)
                self.assertEqual(result, expected)
                self.assertIs(type(result), str)

    def testIndentProducesPrettyOutput(self) -> None:
        """Format JSON with the requested two-space indentation.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(_filter_json()({"a": 1}, indent=2), '{\n  "a": 1\n}')

    def testFallsBackToStrForNonSerializable(self) -> None:
        """Return the object's text when JSON encoding rejects its type.

        Returns
        -------
        None
            No return value.
        """

        class _Unserializable:
            """Provide an unsupported object with a deterministic representation."""

            __slots__ = ()

            def __str__(self) -> str:
                """Return the fallback text used by this fixture.

                Returns
                -------
                str
                    Deterministic text for an unsupported JSON object.
                """
                return "fixture value"

        self.assertEqual(_filter_json()(_Unserializable()), "fixture value")


class TestMarkdownFilter(TestCase):
    """Check the Markdown syntax supported by the registered extensions."""

    def testRendersMarkdownAsPlainStrings(self) -> None:
        """Render all syntax fixtures without marking their HTML as trusted.

        Returns
        -------
        None
            No return value.
        """
        cases = (
            ("# Title", '<h1 id="title">Title</h1>'),
            ("**bold**", "<p><strong>bold</strong></p>"),
            ("", ""),
            ("simple paragraph text", "<p>simple paragraph text</p>"),
            ("*italic*", "<p><em>italic</em></p>"),
        )
        for value, expected in cases:
            with self.subTest(value=value):
                result = _filter_markdown()(value)
                self.assertEqual(result, expected)
                self.assertIs(type(result), str)


class TestFilterBuilders(TestCase):
    """Check callable ownership and escaping in an actual Jinja environment."""

    def testBuildersProduceIndependentCallables(self) -> None:
        """Build a fresh callable for every registration of either filter.

        Returns
        -------
        None
            No return value.
        """
        for builder in (_filter_json, _filter_markdown):
            with self.subTest(builder=builder.__name__):
                first = builder()
                second = builder()
                self.assertTrue(callable(first))
                self.assertTrue(callable(second))
                self.assertIsNot(first, second)

    async def testFilterOutputRemainsSubjectToAutoescaping(self) -> None:
        """Escape script-like input after applying either presentation filter.

        Returns
        -------
        None
            No return value.
        """
        environment = Environment(autoescape=True, enable_async=True)
        environment.filters.update(
            json=_filter_json(),
            markdown=_filter_markdown(),
        )
        for name in ("json", "markdown"):
            with self.subTest(filter=name):
                template = environment.from_string("{{ value | " + name + " }}")
                result = await template.render_async(value="<script>alert(1)</script>")
                self.assertNotIn("<script>", result)
                self.assertIn("&lt;script&gt;", result)
