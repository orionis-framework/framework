from uri_template import URITemplate
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
        """Reject the expansion dependency's draft extensions.

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
