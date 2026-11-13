# ruff: noqa: PT009
# Preserve native TestCase assertions, boundary probes, and fixture signatures.
"""Verify authentication package contracts and behavior."""

from orionis.auth import concerns
from orionis.auth.concerns.authenticatable import Authenticatable
from orionis.auth.concerns.authorizable import Authorizable
from orionis.auth.concerns.functions import model_primary_key
from orionis.auth.concerns.must_verify_email import MustVerifyEmail
from orionis.test import TestCase


class TestConcernsPackage(TestCase):
    """Validate the public surface of the concerns package."""

    def testExportsTheMixinsAndTheirHelper(self) -> None:
        """Resolve every advertised name through the package.

        Validates the entry point applications import their identity
        mixins from.

        Returns
        -------
        None
            No return value.
        """
        self.assertEqual(
            concerns.__all__,
            ["Authenticatable", "Authorizable", "MustVerifyEmail", "model_primary_key"],
        )
        self.assertIs(concerns.Authenticatable, Authenticatable)
        self.assertIs(concerns.Authorizable, Authorizable)
        self.assertIs(concerns.MustVerifyEmail, MustVerifyEmail)
        self.assertIs(concerns.model_primary_key, model_primary_key)
