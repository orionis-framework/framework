from collections.abc import ItemsView, KeysView, ValuesView
from typing import get_args, get_origin, get_type_hints
from orionis.http.payload.estructures.cookies import Cookies
from orionis.test import TestCase


class TestCookieViewAnnotations(TestCase):
    """Keep cookie view annotations resolvable and consistent with their results."""

    def testViewAnnotationsResolveToTheirRuntimeViewTypes(self) -> None:
        """Resolve public annotations without supplying an external namespace."""
        cookies = Cookies("color=blue; empty=")
        for method, view_type, arguments in (
            (Cookies.items, ItemsView, (str, str)),
            (Cookies.keys, KeysView, (str,)),
            (Cookies.values, ValuesView, (str,)),
        ):
            annotation = get_type_hints(method)["return"]
            self.assertIs(get_origin(annotation), view_type)
            self.assertEqual(get_args(annotation), arguments)
            self.assertIsInstance(method(cookies), view_type)

    def testViewOperationsPreserveParsedCookieValues(self) -> None:
        """Preserve ordered values, membership and set operations on cookie views."""
        cookies = Cookies("color=red; empty=; color=blue; name=A%20B")
        items = cookies.items()
        keys = cookies.keys()
        values = cookies.values()
        self.assertEqual(
            list(items), [("color", "blue"), ("empty", ""), ("name", "A B")],
        )
        self.assertEqual(list(keys), ["color", "empty", "name"])
        self.assertEqual(list(values), ["blue", "", "A B"])
        self.assertEqual(keys & {"color", "missing"}, {"color"})
        self.assertEqual(
            items & {("color", "blue"), ("missing", "value")},
            {("color", "blue")},
        )
        self.assertIn("A B", values)
        self.assertEqual(cookies["color"], "blue")
        self.assertEqual(cookies.get("missing", "fallback"), "fallback")
        self.assertEqual(len(items), len(cookies))
