from orionis.http.enums.interfaces import Interface
from orionis.http.payload.body import BodyStream
from orionis.http.payload.estructures.headers import Headers
from orionis.http.payload.estructures.query_params import QueryParams
from orionis.http.payload.form_data import FormData
from orionis.http.payload.media_types import MediaTypeRegistry
from orionis.http.payload.part import MultipartPart
from orionis.http.payload.uploaded_file import UploadedFile
from orionis.test import TestCase

class TestPayloadStructures(TestCase):
    """Validate repeated values, ownership, and slotted payload instances."""

    def testHeadersPreserveBlankAndRepeatedValues(self) -> None:
        """Keep case-insensitive lookup and ordered repeated headers."""
        headers = Headers([("X-Name", ""), ("x-name", "second"), ("Host", "")])
        self.assertEqual(headers.get("X-NAME"), "second")
        self.assertEqual(headers.get("host"), "")
        self.assertEqual(headers.getAll("x-name"), ["", "second"])
        self.assertEqual(headers.count("X-Name"), 2)
        self.assertEqual(headers.count("host"), 1)
        self.assertEqual(headers.count("missing"), 0)
        self.assertEqual(headers.getAll("missing"), [])

    def testHeadersReturnIndependentGroupedLists(self) -> None:
        """Prevent edits to returned header groups from mutating the index."""
        headers = Headers([("X", "1"), ("x", "2"), ("Y", "3")])
        groups = headers.getAll()
        groups["x"].clear()
        groups["y"].append("4")
        self.assertEqual(headers.getAll(), {"x": ["1", "2"], "y": ["3"]})

    def testQueryParamsPreserveOrderAndRepeatedValues(self) -> None:
        """Return the last scalar and all ordered values for repeated keys."""
        params = QueryParams("a=&b=1&a=2&a=3")
        self.assertEqual(params.get("a"), "3")
        self.assertEqual(params.getAll("a"), ["", "2", "3"])
        self.assertEqual(params.getAll("b"), ["1"])
        self.assertEqual(params.getAll("missing"), [])
        self.assertEqual(list(params), [("a", ""), ("b", "1"), ("a", "2"), ("a", "3")])
        values = params.getAll("a")
        values.clear()
        self.assertEqual(params.getList("a"), ["", "2", "3"])

    def testFormPreservesMixedValuesAndDefaultIdentity(self) -> None:
        """Allow fields and uploaded files to share a name without reordering."""
        upload = UploadedFile("f", None)
        with FormData([("a", ""), ("a", upload), ("b", "v")]) as form:
            self.assertIs(form.get("a"), upload)
            self.assertEqual(form.getAll("a"), ["", upload])
            self.assertEqual(form.getAll("b"), ["v"])
            default = ["fallback"]
            self.assertIs(form.get("missing", default), default)
            self.assertEqual(list(form), ["a", "b"])

    def testPayloadContractsDoNotIntroduceInstanceDictionaries(self) -> None:
        """Keep concrete payload object storage limited to declared slots."""
        upload = UploadedFile("f", None)
        try:
            objects = (
                upload,
                BodyStream(Interface.ASGI, None),
                FormData([]),
                MediaTypeRegistry(),
                MultipartPart({"content-disposition": 'form-data; name="f"'}, 1),
            )
            for instance in objects:
                with self.subTest(kind=type(instance).__name__):
                    self.assertFalse(hasattr(instance, "__dict__"))
        finally:
            upload.close()
