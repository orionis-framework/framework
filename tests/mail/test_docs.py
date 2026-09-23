import re
from pathlib import Path
from tempfile import TemporaryDirectory
from types import MappingProxyType
from orionis.foundation.application import Application
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.entities.prepared import PreparedMail
from orionis.test import TestCase

_DOCS = Path(__file__).resolve().parents[2] / "orionis/mail/docs"
_PYTHON_BLOCK = re.compile(r"```python\n(.*?)\n```", re.DOTALL)


class TestMailDocumentation(TestCase):
    def testBothManualsShareTheSameCompilableExamples(self) -> None:
        """Keep bilingual code examples identical and valid for the selected Python."""
        english = _PYTHON_BLOCK.findall(
            (_DOCS / "README.md").read_text(encoding="utf-8"),
        )
        spanish = _PYTHON_BLOCK.findall(
            (_DOCS / "README.es.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(english, spanish)
        self.assertGreaterEqual(len(english), 12)
        for index, source in enumerate(english):
            compile(source, f"mail-documentation-{index}", "exec")

    async def testDocumentedExtensionFactoryUsesTheRealContainer(self) -> None:
        """Execute the documented factory verbatim and store its prepared message."""
        source = (_DOCS / "README.md").read_text(encoding="utf-8")
        example = next(block for block in _PYTHON_BLOCK.findall(source)
                       if "async def archive_factory(" in block)
        namespace = {"__name__": __name__}
        exec(compile(example, "mail-archive-example", "exec"), namespace)  # noqa: S102
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "archive"
            transport = await namespace["archive_factory"](
                Application(), MappingProxyType({"path": str(path)}),
            )
            self.assertIsInstance(transport, IMailTransport)
            prepared = PreparedMail(
                message_id="<documented@example.com>", sender="a@example.com",
                recipients=("b@example.com",),
                mime=b"Subject: Documented factory\r\n\r\nExample\r\n", smtp_utf8=False,
            )
            result = await transport.send(
                prepared, mailer="archive", driver="custom_archive",
            )
            self.assertEqual(result.file_path.parent, path)
            self.assertEqual(result.file_path.read_bytes(), prepared.mime)
