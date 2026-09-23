import typing
from orionis.mail import types as mail_types
from orionis.test import TestCase

class TestMailTypes(TestCase):

    def testPublishesEveryDocumentedAlias(self) -> None:
        """
        Expose the four aliases used across the public mail surface.

        Validates that every alias is a real PEP 695 type alias.
        """
        names = ("Recipients", "MessageCallback", "Delivery", "TransportFactory")
        for name in names:
            alias = getattr(mail_types, name)
            self.assertIsInstance(alias, typing.TypeAliasType)
            self.assertEqual(alias.__name__, name)

    def testRecipientsAcceptsSingleAndCollectedMailboxes(self) -> None:
        """
        Describe one mailbox or a collection of mailboxes.

        Validates the declaration consumed by every recipient method.
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
        """
        Resolve the callback, delivery, and factory aliases eagerly.

        Validates that no forward reference remains unresolvable.
        """
        for name in ("MessageCallback", "Delivery", "TransportFactory"):
            value = getattr(mail_types, name).__value__
            self.assertIs(typing.get_origin(value), typing.get_origin(
                typing.Callable[[int], int],
            ))
