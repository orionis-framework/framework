from orionis.mail.entities.content import Content
from orionis.mail.exceptions import MailCompositionException
from orionis.test import TestCase

class TestContent(TestCase):

    def testDeclaresViewsAndLiteralsSeparately(self) -> None:
        """
        Keep view identifiers and literal bodies in their own fields.

        Validates that a literal is never confused with a template name.
        """
        content = Content(
            view="emails.welcome",
            text_view="emails/welcome.txt",
            data={"name": "Ana"},
        )
        self.assertEqual(content.view, "emails.welcome")
        self.assertEqual(content.text_view, "emails/welcome.txt")
        self.assertIsNone(content.html)
        self.assertIsNone(content.text)

    def testEmptyLiteralIsADeclaredBody(self) -> None:
        """
        Treat an empty string as an intentionally declared body.

        Validates the difference between an empty body and no body at all.
        """
        self.assertEqual(Content(text="").text, "")
        self.assertEqual(Content(html="").html, "")

    def testSnapshotsContainersButNotOpaqueObjects(self) -> None:
        """
        Copy owned context containers without deep-copying user objects.

        Validates that later mutations of the caller's data never leak in.
        """
        service = object()
        data = {"names": ["Ana"], "options": {"enabled": True}, "service": service}
        content = Content(view="emails.welcome", text="", data=data)
        data["names"].append("Luis")
        data["options"]["enabled"] = False

        self.assertEqual(content.data["names"], ("Ana",))
        self.assertTrue(content.data["options"]["enabled"])
        self.assertIs(content.data["service"], service)
        with self.assertRaises(TypeError):
            content.data["new"] = True

    def testCopiesSetsAndRejectsCyclicContainers(self) -> None:
        """
        Protect set context values and reject container cycles.

        Validates that an immutable snapshot is always achievable.
        """
        values = {"first"}
        content = Content(text="text", data={"values": values})
        values.add("second")
        self.assertEqual(content.data["values"], frozenset({"first"}))

        cyclic: dict[str, object] = {}
        cyclic["self"] = cyclic
        with self.assertRaises(MailCompositionException):
            Content(text="text", data=cyclic)

    def testMissingDataBecomesAnEmptyMapping(self) -> None:
        """
        Normalize an absent context into an empty read-only mapping.

        Validates that rendering always receives a mapping.
        """
        content = Content(view="emails.welcome")
        self.assertEqual(dict(content.data), {})

    def testRejectsAbsentConflictingAndInvalidBodies(self) -> None:
        """
        Reject undeclared, conflicting, or wrongly typed bodies.

        Validates that every operation carries exactly one body per format.
        """
        for options in (
            {},
            {"view": "x", "html": ""},
            {"text": "", "text_view": "x"},
            {"view": ""},
            {"text_view": ""},
            {"text": 1},
            {"html": b"bytes"},
            {"text": "x", "data": []},
            {"text": "x", "data": {1: "key"}},
        ):
            with self.assertRaises(MailCompositionException):
                Content(**options)
