# ruff: noqa: TC001
# Keep the application contract available for command dependency injection.
"""Generate and persist an application encryption key."""

from typing import ClassVar
from orionis.console.args.argument import Argument
from orionis.console.base.command import BaseCommand
from orionis.console.enums.actions import ArgumentAction
from orionis.console.output.console import Console
from orionis.environment import Env
from orionis.environment.key.key_generator import SecureKeyGenerator
from orionis.foundation.config.app.enums.ciphers import Cipher
from orionis.foundation.contracts.application import IApplication


class KeyGenerateCommand(BaseCommand):
    """Generate and persist an application encryption key."""

    timestamps: bool = False
    """Timestamps flag used by ``KeyGenerateCommand``."""
    signature: str = "key:generate"
    """Signature identifier: ``key:generate``."""
    description: str = "Generate the application encryption key."
    """Description identifier: ``Generate the application encryption key.``."""
    arguments: ClassVar[list[Argument]] = [
        Argument(
            name_or_flags="--force",
            action=ArgumentAction.STORE_TRUE,
            default=False,
            help="Replace the existing application key.",
        ),
    ]
    """Command-line argument declarations accepted by this command."""

    def handle(
        self,
        app: IApplication,
        console: Console,
    ) -> int:
        """
        Create a key and store it in the application's environment file.

        Parameters
        ----------
        app : orionis.IApplication
            Application providing the configured cipher.
        console : orionis.console.Console
            Console used to report the result.

        Returns
        -------
        int
            Zero when the key is written or preserved; one when persistence fails.
        """
        force = self.getArgument("force", default=False)
        existing_key = Env.get("APP_KEY")
        if existing_key and not force:
            console.warning(
                "APP_KEY is already set. Use --force to replace it.",
                timestamp=False,
            )
            return 0

        cipher = app.config("app.cipher") or Cipher.AES_256_GCM
        generated_key = SecureKeyGenerator.generate(cipher)
        try:
            if not Env.set("APP_KEY", generated_key):
                console.error(
                    "The application key could not be saved.",
                    timestamp=False,
                )
                return 1
        except (OSError, TypeError, ValueError, RuntimeError) as error:
            console.error(
                f"The application key could not be saved: {error}",
                timestamp=False,
            )
            return 1

        console.success("Application key generated and saved.", timestamp=False)
        return 0
