# ruff: noqa: PT009, S603
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
# Run fixed import probes with the active interpreter, without a shell.
import subprocess
import sys
import typing
from inspect import isfunction
from orionis.mail import types as mail_types
from orionis.mail.composer import MailComposer
from orionis.mail.contracts.manager import IMailManager
from orionis.mail.contracts.transport import IMailTransport
from orionis.mail.entities.address import Address, addresses
from orionis.mail.entities.envelope import Envelope
from orionis.mail.entities.options import MailOptions
from orionis.mail.entities.result import MailResult
from orionis.mail.entities.smtp_settings import SmtpSettings
from orionis.mail.mailable import Mailable
from orionis.mail.manager import MailManager
from orionis.mail.message import Message
from orionis.mail.pending import PendingMail
from orionis.mail.transports.file import FileTransport, create_file_transport
from orionis.mail.transports.smtp import SmtpTransport, create_smtp_transport
from orionis.test import TestCase


class TestMailTypes(TestCase):
    def testPublishesEveryDocumentedAlias(self) -> None:
        """Expose the four aliases used across the public mail surface.

        Validates that every alias is a real PEP 695 type alias.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        names = ("Recipients", "MessageCallback", "Delivery", "TransportFactory")
        for name in names:
            alias = getattr(mail_types, name)
            self.assertIsInstance(alias, typing.TypeAliasType)
            self.assertEqual(alias.__name__, name)

    def testRecipientsAcceptsSingleAndCollectedMailboxes(self) -> None:
        """Describe one mailbox or a collection of mailboxes.

        Validates the declaration consumed by every recipient method.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        self.assertEqual(
            typing.get_args(mail_types.Recipients.__value__),
            (
                str,
                mail_types.Address,
                list[str | mail_types.Address],
                tuple[str | mail_types.Address, ...],
            ),
        )

    def testCallbackAliasesResolveToCallables(self) -> None:
        """Resolve the callback, delivery, and factory aliases eagerly.

        Validates that no forward reference remains unresolvable.

        Returns
        -------
        None
            Assertions verify the behavior described above.
        """
        for name in ("MessageCallback", "Delivery", "TransportFactory"):
            value = getattr(mail_types, name).__value__
            self.assertIs(
                typing.get_origin(value),
                typing.get_origin(
                    typing.Callable[[int], int],
                ),
            )

    def testPublicAnnotationsResolveWithoutCallerNamespaces(self) -> None:
        """Resolve public mail annotations for runtime dependency inspection.

        Returns
        -------
        None
            No return value.
        """
        for owner in (
            Address,
            Envelope,
            MailOptions,
            MailResult,
            SmtpSettings,
            Mailable,
            MailComposer,
            MailManager,
            Message,
            PendingMail,
            IMailManager,
            IMailTransport,
            FileTransport,
            SmtpTransport,
        ):
            with self.subTest(owner=owner.__name__):
                typing.get_type_hints(owner)
            for name, member in vars(owner).items():
                method = (
                    member.__func__
                    if isinstance(member, (classmethod, staticmethod))
                    else member
                )
                if isfunction(method) and name != "__annotate_func__":
                    with self.subTest(owner=owner.__name__, method=name):
                        typing.get_type_hints(method)
        for function in (addresses, create_file_transport, create_smtp_transport):
            with self.subTest(function=function.__name__):
                typing.get_type_hints(function)

    def testRuntimeAnnotationsSurviveColdImportOrders(self) -> None:
        """Resolve public aliases and contracts after independent cold imports.

        Returns
        -------
        None
            No return value.
        """
        source = """
import importlib
import sys
from typing import get_type_hints
importlib.import_module(sys.argv[1])
from orionis.mail import types
from orionis.mail.composer import MailComposer
from orionis.mail.contracts.manager import IMailManager
from orionis.mail.entities.address import addresses
from orionis.mail.entities.options import MailOptions
from orionis.mail.entities.result import MailResult
from orionis.mail.pending import PendingMail
for target in (
    addresses, MailComposer.prepare, IMailManager.send,
    MailOptions.__init__, MailResult.__init__, PendingMail.__init__,
):
    assert get_type_hints(target)
for name in ("Recipients", "MessageCallback", "Delivery", "TransportFactory"):
    assert getattr(types, name).__value__
print("runtime mail annotations resolved")
"""
        for module in (
            "orionis.mail.entities.address",
            "orionis.mail.entities.envelope",
            "orionis.mail.message",
            "orionis.mail.types",
            "orionis.mail.pending",
            "orionis.mail.contracts.transport",
            "orionis.mail.contracts.manager",
            "orionis.mail.manager",
        ):
            with self.subTest(module=module):
                result = subprocess.run(
                    [sys.executable, "-B", "-c", source, module],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("runtime mail annotations resolved", result.stdout)
