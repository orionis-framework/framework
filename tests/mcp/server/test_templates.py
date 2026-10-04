"""Check inverse resource routing against full RFC 6570 expansion."""

import unittest

from uri_template import URITemplate

from orionis.mcp.server.primitives import Resource
from orionis.mcp.server.templates import UriMatcher


def _inverse(variables):
    """Bind fixture variables outside the test's iteration scope."""
    def match(_uri):
        """Return declared inverse values for the expansion fixture."""
        return variables

    return staticmethod(match)


class TestTemplates(unittest.TestCase):
    """Use automatic matching only where inverse semantics are unambiguous."""

    def test_simple_string_matching_and_repeated_names(self):
        """Decode percent escapes while preserving repeated-variable identity."""
        definition = type(
            "File", (Resource,), {"uri_template": "demo://users/{name}/{name}"},
        )
        matcher = UriMatcher.compile(definition)
        self.assertEqual(matcher.match("demo://users/a%20b/a%20b"), {"name": "a b"})
        self.assertIsNone(matcher.match("demo://users/a/b"))
        self.assertIsNone(matcher.match("demo://users/a/b/c"))

    def test_all_rfc_operators_with_explicit_inverse(self):
        """An explicit matcher handles full level-four list/map operators."""
        values = {
            "path": "a/b",
            "list": ["one", "two"],
            "keys": {"x": "one", "y": "two"},
        }
        for expression in (
            "{path}",
            "{+path}",
            "{#path}",
            "{.list*}",
            "{/list*}",
            "{;keys*}",
            "{?keys*}",
            "{?path}{&list*}",
            "{path:1}",
        ):
            template = "demo://root/" + expression
            expander = URITemplate(template)
            variables = {key: values[key] for key in expander.variable_names}
            definition = type(
                "FullTemplate",
                (Resource,),
                {
                    "uri_template": template,
                    "match": _inverse(variables),
                },
            )

            with self.subTest(expression=expression):
                matcher = UriMatcher.compile(definition)
                self.assertEqual(matcher.match(expander.expand(**variables)), variables)

    def test_complex_inverse_must_be_explicit(self):
        """Boot fails clearly rather than silently supporting only part of RFC 6570."""
        for template in ("demo://root{?a,b}", "demo://root/{a}{b}"):
            definition = type("Ambiguous", (Resource,), {"uri_template": template})
            with (
                self.subTest(template=template),
                self.assertRaisesRegex(ValueError, "explicit"),
            ):
                UriMatcher.compile(definition)

    def test_reject_non_rfc_extensions(self):
        """The expansion dependency's draft extensions cannot leak into metadata."""
        for expression in (
            "{value=default}",
            "{?name/key}",
            "{value:0000}",
            "{,value}",
        ):
            definition = type(
                "Invalid", (Resource,), {"uri_template": "demo://root/" + expression},
            )
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                UriMatcher.compile(definition)

    def test_custom_matcher_must_round_trip(self):
        """A custom matcher cannot route a URI outside its declared template."""
        definition = type(
            "Wrong",
            (Resource,),
            {
                "uri_template": "demo://root/{name}",
                "match": staticmethod(lambda _uri: {"name": "allowed"}),
            },
        )
        self.assertIsNone(UriMatcher.compile(definition).match("demo://root/other"))
