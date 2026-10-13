from uritemplate import URITemplate
from orionis.mcp.server.primitives import Resource
from orionis.mcp.server.templates import UriMatcher
from orionis.test import TestCase

def _inverse(variables: dict[str, object]) -> staticmethod:
    """Bind fixture variables outside the test's iteration scope.

    Parameters
    ----------
    variables : dict[str, object]
        Values returned by the custom inverse.

    variables : dict[str, object]
        Value supplied for ``variables``.

    Returns
    -------
    staticmethod
        One static inverse with fixed fixture values.
    """

    def match(_uri: str) -> dict[str, object]:
        """Return declared inverse values for the expansion fixture.

        Parameters
        ----------
        _uri : str
            Resource URI supplied to the custom inverse.

        _uri : str
            Value supplied for ``_uri``.

        Returns
        -------
        dict[str, object]
            Variables associated with the fixture.
        """
        return variables

    return staticmethod(match)

class TestTemplates(TestCase):
    """Use automatic matching only where inverse semantics are unambiguous."""

    def testRfcExpansionHasIndependentExpectedUris(self) -> None:
        """Check encoding, operators and absent values against fixed URI fixtures.

        Returns
        -------
        None
            Expansion and inverse verification preserve the declared URI contract.
        """
        cases = (
            ("{name}", {"name": "café /?#+%"},
             "caf%C3%A9%20%2F%3F%23%2B%25"),
            ("{+path}", {"path": "a/b?x=1#part"}, "a/b?x=1#part"),
            ("{#name}", {"name": "a b"}, "#a%20b"),
            ("{name:2}", {"name": "é猫tail"}, "%C3%A9%E7%8C%AB"),
            ("{name:9999}", {"name": "value"}, "value"),
            ("{/items*}", {"items": ["a/b", "c d"]}, "/a%2Fb/c%20d"),
            ("{?keys*}", {"keys": {"a&b": "x=y", "empty": ""}},
             "?a%26b=x%3Dy&empty="),
            ("{;name,empty,missing}", {"name": "a/b", "empty": ""},
             ";name=a%2Fb;empty"),
            ("{?missing,empty,nil,items}{&flag}",
             {"empty": "", "nil": None, "items": [], "flag": True},
             "?empty=&flag=true"),
            ("{?missing}", {}, ""),
            ("{?flag,zero}", {"flag": False, "zero": 0}, "?flag=false&zero=0"),
            ("{var_dict}", {"var_dict": "value"}, "value"),
            ("{?keys*}", {"keys": {"z": "last", "a": "first"}},
             "?z=last&a=first"),
            ("{?items*}", {"items": (True, False, 0)},
             "?items=true&items=false&items=0"),
            ("café/{name}", {"name": "é"}, "caf%C3%A9/%C3%A9"),
            ("{x.y}/{percent%20name}",
             {"x.y": "a", "percent%20name": "b"}, "a/b"),
        )
        for expression, values, expected in cases:
            with self.subTest(expression=expression):
                definition = type("Fixture", (Resource,), {
                    "uri_template": "demo://root/" + expression,
                    "match": _inverse(values),
                })
                matcher = UriMatcher.compile(definition)
                uri = "demo://root/" + expected
                self.assertEqual(matcher.match(uri), values)

    def testSimpleCapturesPreserveUtf8AndLiteralPercentSigns(self) -> None:
        """Decode exactly once and accept either hexadecimal escape case.

        Returns
        -------
        None
            Encoded separators stay inside the variable and UTF-8 remains strict.
        """
        definition = type("Encoded", (Resource,), {
            "uri_template": "demo://root/{name}",
        })
        matcher = UriMatcher.compile(definition)
        self.assertEqual(matcher.match("demo://root/caf%c3%a9%2f%252F"), {
            "name": "café/%2F",
        })
        self.assertEqual(matcher.match("demo://root/"), {"name": ""})
        unicode_literal = type("UnicodeLiteral", (Resource,), {
            "uri_template": "demo://café/{name}",
        })
        self.assertEqual(
            UriMatcher.compile(unicode_literal).match("demo://caf%C3%A9/%E7%8C%AB"),
            {"name": "猫"},
        )
        for uri in ("demo://root/%", "demo://root/%GG", "demo://root/%FF"):
            with self.subTest(uri=uri), self.assertRaises(ValueError):
                matcher.match(uri)

    def testPrefixRejectsCompositeValues(self) -> None:
        """Reject prefix modifiers applied to a list instead of a string.

        Returns
        -------
        None
            Invalid inverse values cannot pass URI verification silently.
        """
        for value in (["first", "second"], {"first": "second"}):
            definition = type("CompositePrefix", (Resource,), {
                "uri_template": "demo://root/{items:2}",
                "match": _inverse({"items": value}),
            })
            with (
                self.subTest(value=value),
                self.assertRaisesRegex(ValueError, "prefix"),
            ):
                UriMatcher.compile(definition).match("demo://root/fi")

    def testSimpleStringMatchingAndRepeatedNames(self) -> None:
        """Decode percent escapes while preserving repeated-variable identity.

        Returns
        -------
        None
            Repeated captures must decode to identical values.
        """
        definition = type(
            "File",
            (Resource,),
            {"uri_template": "demo://users/{name}/{name}"},
        )
        matcher = UriMatcher.compile(definition)
        self.assertEqual(matcher.match("demo://users/a%20b/a%20b"), {"name": "a b"})
        self.assertIsNone(matcher.match("demo://users/a/b"))
        self.assertIsNone(matcher.match("demo://users/a/b/c"))

    def testAllRfcOperatorsWithExplicitInverse(self) -> None:
        """Match full level-four operators with an explicit inverse.

        Returns
        -------
        None
            Every supported operator round-trips its fixture variables.
        """
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

    def testComplexInverseMustBeExplicit(self) -> None:
        """Reject ambiguous captures before accepting client-supplied URIs.

        Returns
        -------
        None
            Adjacent and overlapping variable captures require an explicit inverse.
        """
        for template in (
            "demo://root{?a,b}",
            "demo://root/{a}{b}",
            "demo://root/{a}-{b}",
            "demo://root/{a}.x{b}",
            "demo://root/{a}%2F{b}",
        ):
            definition = type("Ambiguous", (Resource,), {"uri_template": template})
            with (
                self.subTest(template=template),
                self.assertRaisesRegex(ValueError, "explicit"),
            ):
                UriMatcher.compile(definition)

    def testRejectNonRfcExtensions(self) -> None:
        """Reject malformed syntax and nonstandard URI template extensions.

        Returns
        -------
        None
            Unsupported draft expressions never enter compiled metadata.
        """
        for expression in (
            "{value=default}",
            "{?name/key}",
            "{value:0000}",
            "{,value}",
            "{value[]}",
            "{value:10000}",
            "{value:2*}",
            "{value",
            "value}",
            "{}",
        ):
            definition = type(
                "Invalid",
                (Resource,),
                {"uri_template": "demo://root/" + expression},
            )
            with self.subTest(expression=expression), self.assertRaises(ValueError):
                UriMatcher.compile(definition)

    def testCustomMatcherMustRoundTrip(self) -> None:
        """Reject custom inverse results outside the declared template.

        Returns
        -------
        None
            A URI mismatch cannot resolve a resource.
        """
        definition = type(
            "Wrong",
            (Resource,),
            {
                "uri_template": "demo://root/{name}",
                "match": staticmethod(lambda _uri: {"name": "allowed"}),
            },
        )
        self.assertIsNone(UriMatcher.compile(definition).match("demo://root/other"))

    def testAmbiguousDelimitersRemainAvailableWithAnExplicitInverse(self) -> None:
        """Allow a custom inverse to define ambiguous variable boundaries.

        Returns
        -------
        None
            A developer-supplied inverse still passes the expansion check.
        """
        values = {"first": "a-b", "second": "c"}
        definition = type(
            "Delimited",
            (Resource,),
            {
                "uri_template": "demo://root/{first}-{second}",
                "match": _inverse(values),
            },
        )
        self.assertEqual(
            UriMatcher.compile(definition).match("demo://root/a-b-c"),
            values,
        )

    def testCustomInverseCannotAddAnUndeclaredVariable(self) -> None:
        """Reject extra custom variables even when declared variables are absent.

        Returns
        -------
        None
            Incomparable variable sets cannot bypass the declaration check.
        """
        definition = type(
            "ExtraVariable",
            (Resource,),
            {
                "uri_template": "demo://root/{name}",
                "match": _inverse({"other": "value"}),
            },
        )
        with self.assertRaises(ValueError):
            UriMatcher.compile(definition).match("demo://root/value")

    def testLongInvalidVariableIsRejectedAtCompilation(self) -> None:
        """Reject a long malformed variable without constructing a route inverse.

        Returns
        -------
        None
            The expression validator rejects an invalid suffix.
        """
        definition = type(
            "LongVariable",
            (Resource,),
            {
                "uri_template": "demo://root/{" + "part." * 2048 + "!}",
            },
        )
        with self.assertRaises(ValueError):
            UriMatcher.compile(definition)
