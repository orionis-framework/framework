from orionis.schemas.meta.document import DocumentMetadata
from orionis.schemas.meta.validation import ValidationMetadata
from orionis.schemas.metadata import (
    Description,
    Examples,
    Extra,
    ExtraJsonSchema,
    Message,
    Title,
)
from orionis.test import TestCase

class TestTitleMetadata(TestCase):

    def testTitleStoresValue(self) -> None:
        """Instantiate Title and verify the value attribute.

        Validates that the constructor stores the provided title string
        on the ``value`` attribute.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        t = Title("My Field")
        self.assertEqual(t.value, "My Field")

    def testTitleIsDocumentMetadata(self) -> None:
        """Confirm Title inherits from DocumentMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(Title("x"), DocumentMetadata)
        self.assertIsInstance(Title("x"), ValidationMetadata)

    def testTitleIsFrozen(self) -> None:
        """Confirm Title instances are immutable.

        Validates that attempting to mutate the value attribute raises
        an exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        t = Title("label")
        with self.assertRaises(AttributeError):
            t.value = "other"  # type: ignore[misc]

    def testTitleEquality(self) -> None:
        """Verify equality between Title instances with the same value.

        Validates the frozen dataclass __eq__ by value semantics.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Title("A"), Title("A"))
        self.assertNotEqual(Title("A"), Title("B"))

class TestDescriptionMetadata(TestCase):

    def testDescriptionStoresValue(self) -> None:
        """Instantiate Description and verify the value attribute.

        Validates that the provided description string is stored
        on the ``value`` attribute.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = Description("A descriptive text.")
        self.assertEqual(d.value, "A descriptive text.")

    def testDescriptionIsDocumentMetadata(self) -> None:
        """Confirm Description inherits from DocumentMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(Description("x"), DocumentMetadata)

    def testDescriptionIsFrozen(self) -> None:
        """Confirm Description instances are immutable.

        Validates that attempting to mutate the value attribute raises
        an exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        d = Description("text")
        with self.assertRaises(AttributeError):
            d.value = "changed"  # type: ignore[misc]

class TestExamplesMetadata(TestCase):

    def testExamplesStoresValues(self) -> None:
        """Instantiate Examples and verify the values attribute.

        Validates that the provided list of example values is stored
        on the ``values`` attribute.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        e = Examples([1, "two", 3.0])
        self.assertEqual(e.values, [1, "two", 3.0])

    def testExamplesIsDocumentMetadata(self) -> None:
        """Confirm Examples inherits from DocumentMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(Examples([]), DocumentMetadata)

    def testExamplesEmptyListIsAccepted(self) -> None:
        """Accept an empty list as the values argument of Examples.

        Validates that no error is raised when an empty list is supplied
        and the values attribute reflects it.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        e = Examples([])
        self.assertEqual(e.values, [])

class TestExtraJsonSchemaMetadata(TestCase):

    def testExtraJsonSchemaStoresData(self) -> None:
        """Instantiate ExtraJsonSchema and verify the data attribute.

        Validates that the provided dict is stored on the ``data``
        attribute without modification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        payload = {"readOnly": True, "deprecated": False}
        e = ExtraJsonSchema(payload)
        self.assertEqual(e.data, payload)

    def testExtraJsonSchemaIsDocumentMetadata(self) -> None:
        """Confirm ExtraJsonSchema inherits from DocumentMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(ExtraJsonSchema({}), DocumentMetadata)

    def testExtraJsonSchemaEmptyDictIsAccepted(self) -> None:
        """Accept an empty dict as the data argument of ExtraJsonSchema.

        Validates that no error is raised and the attribute is empty.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        e = ExtraJsonSchema({})
        self.assertEqual(e.data, {})

class TestExtraMetadata(TestCase):

    def testExtraStoresData(self) -> None:
        """Instantiate Extra and verify the data attribute.

        Validates that the provided dict is stored on the ``data``
        attribute without modification.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        payload = {"custom_key": "custom_value"}
        e = Extra(payload)
        self.assertEqual(e.data, payload)

    def testExtraIsDocumentMetadata(self) -> None:
        """Confirm Extra inherits from DocumentMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(Extra({}), DocumentMetadata)

class TestMessageMetadata(TestCase):

    def testMessageStoresText(self) -> None:
        """Instantiate Message and verify the text attribute.

        Validates that the provided error message string is stored
        on the ``text`` attribute.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        m = Message("Must be a string.")
        self.assertEqual(m.text, "Must be a string.")

    def testMessageIsDocumentMetadata(self) -> None:
        """Confirm Message inherits from DocumentMetadata.

        Validates the class hierarchy for isinstance checks.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertIsInstance(Message("x"), DocumentMetadata)
        self.assertIsInstance(Message("x"), ValidationMetadata)

    def testMessageIsFrozen(self) -> None:
        """Confirm Message instances are immutable.

        Validates that attempting to mutate the text attribute raises
        an exception.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        m = Message("error")
        with self.assertRaises(AttributeError):
            m.text = "changed"  # type: ignore[misc]

    def testMessageEquality(self) -> None:
        """Verify equality between Message instances with the same text.

        Validates the frozen dataclass __eq__ by value semantics.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(Message("a"), Message("a"))
        self.assertNotEqual(Message("a"), Message("b"))
