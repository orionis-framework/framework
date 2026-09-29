from orionis.test import TestCase
from orionis.view.filters import _filter_json, _filter_markdown

_jsonify = _filter_json()
_markdown = _filter_markdown()

class TestJsonifyFilter(TestCase):

    def testSerializesDictToJson(self) -> None:
        """
        Serialise a dictionary to a JSON string.

        Validates that a plain dict is encoded as a valid JSON object
        string with both key and value present in the output.
        """
        result = _jsonify({"key": "value"})
        self.assertIn('"key"', result)
        self.assertIn('"value"', result)

    def testSerializesListToJson(self) -> None:
        """
        Serialise a list to a compact JSON array string.

        Validates that a list of integers is encoded compactly without
        extra whitespace in the default mode.
        """
        result = _jsonify([1, 2, 3])
        self.assertEqual(result, "[1,2,3]")

    def testSerializesNoneToNull(self) -> None:
        """
        Serialise None to the JSON null literal.

        Validates that Python's None maps to the JSON null keyword.
        """
        result = _jsonify(None)
        self.assertEqual(result, "null")

    def testSerializesIntegerToNumericString(self) -> None:
        """
        Serialise an integer to its JSON numeric representation.

        Validates that numeric types are encoded without surrounding
        quotes in the output.
        """
        result = _jsonify(42)
        self.assertEqual(result, "42")

    def testIndentProducesPrettyOutput(self) -> None:
        """
        Pretty-print JSON when an indent value is supplied.

        Validates that the indent parameter triggers formatted output
        containing newlines and indentation characters.
        """
        result = _jsonify({"a": 1}, indent=2)
        self.assertIn("\n", result)

    def testDefaultModeIsCompact(self) -> None:
        """
        Produce compact JSON output when no indent is specified.

        Validates that the default output contains no unnecessary
        whitespace between tokens.
        """
        result = _jsonify({"a": 1})
        self.assertNotIn("\n", result)

    def testFallsBackToStrForNonSerializable(self) -> None:
        """
        Fall back to str() for values that cannot be JSON-serialised.

        Validates that non-serialisable objects produce a string
        representation instead of raising an exception.
        """

        class _Unserializable:
            pass

        result = _jsonify(_Unserializable())
        self.assertIsInstance(result, str)

    def testAlwaysReturnsString(self) -> None:
        """
        Confirm _jsonify always returns a str regardless of input type.

        Validates that the output type is str for common Python values
        so Jinja2 templates receive a printable result.
        """
        self.assertIsInstance(_jsonify("hello"), str)
        self.assertIsInstance(_jsonify(0), str)
        self.assertIsInstance(_jsonify([]), str)

    def testSerializesBooleanTrue(self) -> None:
        """
        Serialise boolean True to the JSON true literal.

        Validates that Python's True maps to the lowercase JSON boolean.
        """
        result = _jsonify(True)
        self.assertEqual(result, "true")

    def testSerializesBooleanFalse(self) -> None:
        """
        Serialise boolean False to the JSON false literal.

        Validates that Python's False maps to the lowercase JSON boolean.
        """
        result = _jsonify(False)
        self.assertEqual(result, "false")


class TestMarkdownFilter(TestCase):

    def testConvertsH1HeadingToHtml(self) -> None:
        """
        Render a Markdown H1 heading to an HTML h1 element.

        Validates that ATX-style headings are converted to the
        corresponding HTML heading tag (with or without attributes).
        """
        result = _markdown("# Title")
        self.assertIn("<h1", result)

    def testConvertsBoldToStrong(self) -> None:
        """
        Render Markdown bold syntax to an HTML strong element.

        Validates that double-asterisk emphasis is converted to the
        HTML <strong> tag.
        """
        result = _markdown("**bold**")
        self.assertIn("<strong>", result)

    def testHandlesEmptyString(self) -> None:
        """
        Render an empty Markdown string without raising an exception.

        Validates that an empty input is handled gracefully and always
        returns a string value.
        """
        result = _markdown("")
        self.assertIsInstance(result, str)

    def testAlwaysReturnsString(self) -> None:
        """
        Confirm _markdown always returns a str type.

        Validates that the output type is str regardless of the input
        content or Markdown syntax used.
        """
        result = _markdown("simple paragraph text")
        self.assertIsInstance(result, str)

    def testConvertsItalicToEm(self) -> None:
        """
        Render Markdown italic syntax to an HTML em element.

        Validates that single-asterisk emphasis is converted to the
        HTML <em> tag.
        """
        result = _markdown("*italic*")
        self.assertIn("<em>", result)


class TestFilterBuilders(TestCase):

    def testJsonBuilderReturnsCallable(self) -> None:
        """
        Verify _filter_json returns a callable filter.

        Validates that Jinja2 can invoke the built filter with a
        template value at render time without a TypeError.
        """
        self.assertTrue(callable(_filter_json()))

    def testMarkdownBuilderReturnsCallable(self) -> None:
        """
        Verify _filter_markdown returns a callable filter.

        Validates that Jinja2 can invoke the built filter with a
        template value at render time without a TypeError.
        """
        self.assertTrue(callable(_filter_markdown()))

    def testBuilderProducesIndependentCallables(self) -> None:
        """
        Confirm each call to _filter_json builds a new callable.

        Validates that the builder does not share a cached closure
        between registrations.
        """
        self.assertIsNot(_filter_json(), _filter_json())

    def testJsonFilterProducesSameOutputAsJsonify(self) -> None:
        """
        Confirm a freshly built json filter matches the module callable.

        Validates that the filter produces the same output as the
        callable built at import time with the same argument.
        """
        self.assertEqual(_filter_json()(42), _jsonify(42))

    def testMarkdownFilterProducesSameOutputAsMarkdown(self) -> None:
        """
        Confirm a freshly built markdown filter matches the module callable.

        Validates that the filter produces the same output as the
        callable built at import time with the same argument.
        """
        self.assertEqual(_filter_markdown()("# Title"), _markdown("# Title"))
